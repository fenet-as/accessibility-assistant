"""Grounded tutoring use case: retrieve, apply the rejection rule, then generate with citations."""

import threading
from collections import OrderedDict
from typing import Optional, Tuple

from assistant.domain.language import detect_language
from assistant.domain.messages import not_found_response
from assistant.domain.models import ChatRequest, ChatResponse
from assistant.domain.ports import AIProvider
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.retrieval import BM25Index

TOP_K = 3
CacheKey = Tuple[int, str, str, str, str]


class AnswerCache:
    """Bounded LRU cache. Many learners in one cohort ask the same questions."""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._items: "OrderedDict[CacheKey, ChatResponse]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: CacheKey) -> Optional[ChatResponse]:
        with self._lock:
            value = self._items.get(key)
            if value is not None:
                self._items.move_to_end(key)
            return value

    def put(self, key: CacheKey, value: ChatResponse) -> None:
        if self.max_size <= 0:
            return
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class TutorService:
    def __init__(
        self,
        store: ChunkStore,
        provider: AIProvider,
        relevance_threshold: float = 0.35,
        cache_size: int = 1024,
    ):
        self.store = store
        self.provider = provider
        self.relevance_threshold = relevance_threshold
        self.cache = AnswerCache(cache_size)
        self._reload_lock = threading.Lock()
        self._index_version = -1
        self._index = BM25Index([])
        self.reload()

    @property
    def indexed_chunks(self) -> int:
        return len(self._index)

    def reload(self) -> None:
        """Rebuild the index from disk and swap it in; in-flight requests keep the old one."""
        with self._reload_lock:
            version = self.store.version
            self._index = BM25Index(self.store.load())
            self._index_version = version
            self.cache.clear()

    def _refresh_if_changed(self) -> None:
        # Another worker process may have ingested a course; one stat() call detects it.
        if self.store.version != self._index_version:
            self.reload()

    def answer(self, request: ChatRequest) -> ChatResponse:
        self._refresh_if_changed()
        language = detect_language(request.message, request.language)

        key = (self._index_version, request.scope, language, request.mode, request.message.strip().lower())
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        passages = self._index.search(request.message, top_k=TOP_K, scope=request.scope)
        if not passages or passages[0].score < self.relevance_threshold:
            response = not_found_response(language)
        else:
            response = self.provider.generate(
                question=request.message,
                passages=passages,
                language=language,
                simple=request.simple,
            )

        self.cache.put(key, response)
        return response
