"""Rate limiting, daily token budget and in-flight request deduplication.

Uses Redis when REDIS_URL is set; otherwise an in-memory sliding window.
Health reports which backend is active.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LimitResult:
    allowed: bool
    retry_after: int = 0
    reason: str = ""


class _MemoryWindow:
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> LimitResult:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = max(1, int(window_seconds - (now - bucket[0])))
                return LimitResult(False, retry_after=retry, reason="rate_limit")
            bucket.append(now)
            return LimitResult(True)


class RateLimiter:
    def __init__(
        self,
        redis_url: str = "",
        *,
        session_per_min: int = 20,
        ip_per_min: int = 60,
        stt_per_min: int = 6,
        daily_token_budget: int = 0,
        daily_cost_budget_usd: float = 0.0,
    ):
        self.session_per_min = session_per_min
        self.ip_per_min = ip_per_min
        self.stt_per_min = stt_per_min
        self.daily_token_budget = daily_token_budget
        self.daily_cost_budget_usd = daily_cost_budget_usd
        self._memory = _MemoryWindow()
        self._redis = None
        self.backend = "memory"
        self._inflight: Dict[str, threading.Event] = {}
        self._inflight_lock = threading.Lock()
        self._budget_tokens = 0
        self._budget_cost = 0.0
        self._budget_day = ""
        self._budget_lock = threading.Lock()
        if redis_url:
            try:
                import redis

                client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
                client.ping()
                self._redis = client
                self.backend = "redis"
            except Exception:
                logger.warning("Redis unavailable for rate limiting; using in-memory limiter", exc_info=True)

    def status(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "session_per_min": self.session_per_min,
            "ip_per_min": self.ip_per_min,
            "stt_per_min": self.stt_per_min,
            "daily_token_budget": self.daily_token_budget or None,
            "budget": self.budget_snapshot(),
        }

    def _redis_hit(self, key: str, limit: int, window_seconds: int = 60) -> LimitResult:
        assert self._redis is not None
        try:
            count = self._redis.incr(key)
            if count == 1:
                self._redis.expire(key, window_seconds)
            if count > limit:
                ttl = int(self._redis.ttl(key) or window_seconds)
                return LimitResult(False, retry_after=max(1, ttl), reason="rate_limit")
            return LimitResult(True)
        except Exception:
            logger.warning("Redis rate-limit error; falling back to memory", exc_info=True)
            self.backend = "memory_fallback"
            return self._memory.hit(key, limit, window_seconds)

    def check(self, *, session_id: str = "", ip: str = "", kind: str = "chat") -> LimitResult:
        if kind == "stt":
            limit = self.stt_per_min
            key = f"alx:rl:stt:{ip or session_id or 'anon'}"
            return self._redis_hit(key, limit) if self._redis else self._memory.hit(key, limit)
        # Session + IP windows for chat
        if session_id:
            key = f"alx:rl:session:{session_id}"
            result = self._redis_hit(key, self.session_per_min) if self._redis else self._memory.hit(key, self.session_per_min)
            if not result.allowed:
                return result
        if ip:
            key = f"alx:rl:ip:{ip}"
            result = self._redis_hit(key, self.ip_per_min) if self._redis else self._memory.hit(key, self.ip_per_min)
            if not result.allowed:
                return result
        return LimitResult(True)

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def record_budget(self, *, tokens: int = 0, cost_usd: float = 0.0) -> Dict[str, Any]:
        day = self._today()
        if self._redis:
            try:
                tkey = f"alx:budget:tokens:{day}"
                ckey = f"alx:budget:cost:{day}"
                if tokens:
                    self._redis.incrby(tkey, int(tokens))
                    self._redis.expire(tkey, 86400 * 2)
                if cost_usd:
                    self._redis.incrbyfloat(ckey, float(cost_usd))
                    self._redis.expire(ckey, 86400 * 2)
                return self.budget_snapshot()
            except Exception:
                logger.warning("Redis budget write failed", exc_info=True)
        with self._budget_lock:
            if self._budget_day != day:
                self._budget_day = day
                self._budget_tokens = 0
                self._budget_cost = 0.0
            self._budget_tokens += max(0, tokens)
            self._budget_cost += max(0.0, cost_usd)
        return self.budget_snapshot()

    def budget_snapshot(self) -> Dict[str, Any]:
        day = self._today()
        tokens = self._budget_tokens
        cost = self._budget_cost
        if self._redis:
            try:
                tokens = int(self._redis.get(f"alx:budget:tokens:{day}") or 0)
                cost = float(self._redis.get(f"alx:budget:cost:{day}") or 0.0)
            except Exception:
                pass
        token_ratio = (tokens / self.daily_token_budget) if self.daily_token_budget else 0.0
        cost_ratio = (cost / self.daily_cost_budget_usd) if self.daily_cost_budget_usd else 0.0
        ratio = max(token_ratio, cost_ratio)
        level = "ok"
        if ratio >= 1.0:
            level = "exhausted"
        elif ratio >= 0.9:
            level = "warning"
        return {
            "day": day,
            "tokens_used": tokens,
            "cost_usd": round(cost, 6),
            "ratio": round(ratio, 3),
            "level": level,
        }

    def budget_exhausted(self) -> bool:
        return self.budget_snapshot()["level"] == "exhausted"

    def acquire_inflight(self, key: str) -> Tuple[bool, Optional[threading.Event]]:
        """Return (is_leader, wait_event). Leader runs the work; followers wait on the event."""
        with self._inflight_lock:
            existing = self._inflight.get(key)
            if existing:
                return False, existing
            event = threading.Event()
            self._inflight[key] = event
            return True, event

    def release_inflight(self, key: str) -> None:
        with self._inflight_lock:
            event = self._inflight.pop(key, None)
            if event:
                event.set()
