"""Exact-response cache: Redis when available, otherwise in-memory TTL dict.

Cache keys include course scope, language, normalized question, simple mode,
knowledge-base version, model/prompt version, and a short history fingerprint
so follow-up answers never collide across topics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from assistant.config import Settings
from assistant.domain.models import ChatResponse, ChatStatus, Citation, ConversationTurn
from assistant.infrastructure.text_analysis import normalize_text

logger = logging.getLogger(__name__)

# Bump when system prompts or answer shaping change so exact-cache entries invalidate.
PROMPT_VERSION = "hybrid-v3"

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


def normalize_question(question: str) -> str:
    collapsed = " ".join((question or "").split())
    return normalize_text(collapsed)


def history_fingerprint(history: Optional[Sequence[ConversationTurn]] = None) -> str:
    """Stable short digest of recent turns so cached answers stay topic-bound."""
    if not history:
        return ""
    parts: List[str] = []
    for turn in list(history)[-4:]:
        role = getattr(turn, "role", "") or ""
        content = getattr(turn, "content", "") or ""
        parts.append(f"{role}:{normalize_question(content)[:120]}")
    if not parts:
        return ""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def cache_key_parts(
    *,
    scope: str,
    language: str,
    question: str,
    simple: bool,
    kb_version: str,
    model_version: str,
    history_fp: str = "",
) -> str:
    normalized = normalize_question(question)
    raw = "|".join([
        scope,
        language,
        normalized,
        "1" if simple else "0",
        kb_version,
        model_version,
        history_fp or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_cacheable(response: ChatResponse, passages_sections: Tuple[str, ...]) -> bool:
    if response.status != ChatStatus.ANSWERED:
        return False
    if not response.answer.strip():
        return False
    # Course-grounded answers may cite sections; general-knowledge answers may cite none.
    # Never cache a response that points at a section we did not retrieve.
    allowed = {s.lower() for s in passages_sections if s}
    for citation in response.citations:
        if citation.section.lower() not in allowed:
            return False
    if response.citations:
        return True
    # Empty citations are cacheable only for explicit general-knowledge answers.
    return response.answer_source in ("cloud_general", "local") and not allowed


class _MemoryTTL:
    def __init__(self, ttl: int, max_entries: int = 4096):
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, payload = item
            if expires < now:
                del self._data[key]
                return None
            return payload

    def set(self, key: str, payload: str) -> None:
        with self._lock:
            if len(self._data) >= self.max_entries:
                oldest = min(self._data.items(), key=lambda pair: pair[1][0])[0]
                del self._data[oldest]
            self._data[key] = (time.time() + self.ttl, payload)

    def clear(self) -> int:
        with self._lock:
            count = len(self._data)
            self._data.clear()
            return count

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class AnswerCache:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._memory = _MemoryTTL(settings.cache_ttl_seconds, settings.cache_max_entries)
        self._redis = None
        if settings.enable_exact_cache and settings.redis_url and redis is not None:
            try:
                client = redis.from_url(settings.redis_url, decode_responses=True)
                client.ping()
                self._redis = client
                logger.info("Exact-answer cache using Redis at %s", settings.redis_url.split("@")[-1])
            except Exception:
                logger.warning("Redis unavailable; using in-memory exact-answer cache", exc_info=True)

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def clear(self) -> Dict[str, Any]:
        """Drop all exact-answer entries (dev/admin). Returns how many were cleared when known."""
        cleared_memory = self._memory.clear()
        cleared_redis = 0
        if self._redis:
            try:
                keys = list(self._redis.scan_iter(match="alx:answer:*", count=200))
                if keys:
                    cleared_redis = int(self._redis.delete(*keys))
            except Exception:
                logger.warning("Redis cache clear failed", exc_info=True)
        return {
            "backend": self.backend,
            "cleared_memory": cleared_memory,
            "cleared_redis": cleared_redis,
        }

    def size_hint(self) -> Dict[str, Any]:
        hint: Dict[str, Any] = {"backend": self.backend, "memory_entries": len(self._memory)}
        if self._redis:
            try:
                hint["redis_answer_keys"] = sum(1 for _ in self._redis.scan_iter(match="alx:answer:*", count=200))
            except Exception:
                hint["redis_answer_keys"] = None
        return hint

    def make_key(
        self,
        *,
        scope: str,
        language: str,
        question: str,
        simple: bool,
        kb_version: str,
        model_version: str,
        history: Optional[Sequence[ConversationTurn]] = None,
        history_fp: Optional[str] = None,
    ) -> str:
        fp = history_fp if history_fp is not None else history_fingerprint(history)
        return cache_key_parts(
            scope=scope,
            language=language,
            question=question,
            simple=simple,
            kb_version=kb_version,
            model_version=model_version,
            history_fp=fp,
        )

    def get(self, key: str) -> Optional[ChatResponse]:
        if not self.settings.enable_exact_cache:
            return None
        try:
            payload = self._redis.get(f"alx:answer:{key}") if self._redis else self._memory.get(key)
            if not payload:
                return None
            data = json.loads(payload)
            expires_at = data.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < datetime.now(timezone.utc):
                        return None
                except ValueError:
                    pass
            # Preserve the original provider; mark the hit via cache_hit + answer_source.
            response = ChatResponse(
                status=ChatStatus(data["status"]),
                language=data["language"],
                answer=data["answer"],
                citations=[Citation(**c) for c in data.get("citations", [])],
                actions=list(data.get("actions", [])),
                confidence=data.get("confidence"),
                suggestions=list(data.get("suggestions", [])),
                language_confidence=data.get("language_confidence"),
                language_overridden=bool(data.get("language_overridden")),
                translation_fallback=bool(data.get("translation_fallback")),
                provider=data.get("provider"),
                cache_hit=True,
                answer_source="cache",
                source_type="cache",
                connectivity=data.get("connectivity") or "online",
                course_id=data.get("course_id") or data.get("scope"),
                fallback_reason=data.get("fallback_reason"),
                question_type=data.get("question_type"),
            )
            return response
        except Exception:
            logger.debug("Cache read failed for key %s", key, exc_info=True)
            return None

    def set(
        self,
        key: str,
        response: ChatResponse,
        *,
        question: str = "",
        scope: str = "",
        kb_version: str = "",
        model_version: str = "",
        history_fp: str = "",
        answer_mode: str = "",
    ) -> None:
        if not self.settings.enable_exact_cache:
            return
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + self.settings.cache_ttl_seconds
        expires_at = datetime.fromtimestamp(expires, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        payload = json.dumps({
            "status": response.status.value,
            "language": response.language,
            "answer": response.answer,
            "citations": [c.model_dump() for c in response.citations],
            "actions": response.actions,
            "confidence": response.confidence,
            "suggestions": response.suggestions,
            "language_confidence": response.language_confidence,
            "language_overridden": response.language_overridden,
            "translation_fallback": response.translation_fallback,
            "provider": response.provider,
            "answer_source": response.answer_source,
            "source_type": response.source_type,
            "connectivity": response.connectivity or "online",
            "fallback_reason": response.fallback_reason,
            "question_type": response.question_type,
            # Cache metadata (Phase 6).
            "question": question,
            "scope": scope or response.course_id or "",
            "course_id": scope or response.course_id or "",
            "kb_version": kb_version,
            "model_version": model_version or PROMPT_VERSION,
            "prompt_version": PROMPT_VERSION,
            "answer_mode": answer_mode,
            "history_fingerprint": history_fp,
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": expires_at,
        })
        try:
            if self._redis:
                self._redis.setex(f"alx:answer:{key}", self.settings.cache_ttl_seconds, payload)
            else:
                self._memory.set(key, payload)
        except Exception:
            logger.debug("Cache write failed for key %s", key, exc_info=True)
