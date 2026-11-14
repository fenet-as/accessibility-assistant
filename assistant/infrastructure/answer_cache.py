"""Exact-response cache: Redis when available, otherwise in-memory TTL dict."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from assistant.config import Settings
from assistant.domain.models import ChatResponse, ChatStatus, Citation
from assistant.infrastructure.text_analysis import normalize_text

logger = logging.getLogger(__name__)

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


def normalize_question(question: str) -> str:
    collapsed = " ".join((question or "").split())
    return normalize_text(collapsed)


def cache_key_parts(
    *,
    scope: str,
    language: str,
    question: str,
    simple: bool,
    kb_version: str,
    model_version: str,
) -> str:
    normalized = normalize_question(question)
    raw = "|".join([scope, language, normalized, "1" if simple else "0", kb_version, model_version])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_cacheable(response: ChatResponse, passages_sections: Tuple[str, ...]) -> bool:
    if response.status != ChatStatus.ANSWERED:
        return False
    if not response.answer.strip():
        return False
    if not response.citations:
        return False
    # Citations must point at sections we actually retrieved (no stale refs).
    allowed = {s.lower() for s in passages_sections if s}
    for citation in response.citations:
        if citation.section.lower() not in allowed:
            return False
    return True


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

    def make_key(
        self,
        *,
        scope: str,
        language: str,
        question: str,
        simple: bool,
        kb_version: str,
        model_version: str,
    ) -> str:
        return cache_key_parts(
            scope=scope,
            language=language,
            question=question,
            simple=simple,
            kb_version=kb_version,
            model_version=model_version,
        )

    def get(self, key: str) -> Optional[ChatResponse]:
        if not self.settings.enable_exact_cache:
            return None
        try:
            payload = self._redis.get(f"alx:answer:{key}") if self._redis else self._memory.get(key)
            if not payload:
                return None
            data = json.loads(payload)
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
            )
            return response
        except Exception:
            logger.debug("Cache read failed for key %s", key, exc_info=True)
            return None

    def set(self, key: str, response: ChatResponse) -> None:
        if not self.settings.enable_exact_cache:
            return
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
        })
        try:
            if self._redis:
                self._redis.setex(f"alx:answer:{key}", self.settings.cache_ttl_seconds, payload)
            else:
                self._memory.set(key, payload)
        except Exception:
            logger.debug("Cache write failed for key %s", key, exc_info=True)