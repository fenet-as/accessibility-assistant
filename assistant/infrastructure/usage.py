"""In-process AI usage accounting (cache hits, provider calls, approximate tokens)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class UsageCounters:
    cache_hits: int = 0
    cache_misses: int = 0
    provider_requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    faq_answers: int = 0
    cloud_answers: int = 0
    local_answers: int = 0
    estimated_cost_usd: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "provider_requests": self.provider_requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "faq_answers": self.faq_answers,
            "cloud_answers": self.cloud_answers,
            "local_answers": self.local_answers,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


class UsageTracker:
    """Thread-safe counters for observability and hackathon demos."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters = UsageCounters()

    def record_cache_hit(self) -> None:
        with self._lock:
            self._counters.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._counters.cache_misses += 1

    def record_provider_request(self, provider: str) -> None:
        with self._lock:
            self._counters.provider_requests += 1
            if provider == "offline_faq":
                self._counters.faq_answers += 1
            elif provider == "cloud_gemini":
                self._counters.cloud_answers += 1
            elif provider == "local_model":
                self._counters.local_answers += 1

    def record_tokens(self, *, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0) -> None:
        with self._lock:
            self._counters.input_tokens += max(0, input_tokens)
            self._counters.output_tokens += max(0, output_tokens)
            self._counters.estimated_cost_usd += max(0.0, cost_usd)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._counters.as_dict()