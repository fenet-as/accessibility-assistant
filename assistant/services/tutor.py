"""Grounded tutoring use case: retrieve, decide by confidence, then generate with citations.

- High confidence: answer from the retrieved passages only.
- Medium confidence: widen retrieval; answer if several sections together cover the question,
  otherwise ask the learner to clarify (with section suggestions).
- Low confidence: not_found, offering a human tutor.
Only the selected passages (never the whole course) reach the AI provider.
"""

import re
import threading
from typing import Any, List, Optional

from assistant.domain.knowledge import compute_kb_version
from assistant.domain.language import detect_language_with_confidence
from assistant.domain.messages import clarification_response, not_found_response
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.retrieval import BM25Index, RetrievalResult

TOP_K = 3
WIDE_K = 8
MAX_SUGGESTIONS = 3
HIGH_CONFIDENCE = 0.6

FOLLOW_UP_MARKERS = {
    # English demonstratives and follow-up markers
    "that", "this", "these", "those", "it", "more", "example", "examples",
    "elaborate", "clarify", "detail", "details",
    # Amharic demonstratives and follow-up markers
    "ይህ", "ይህን", "ያ", "ያንን", "ስለዚህ", "የበለጠ", "ማብራሪያ", "ምሳሌ", "ለምሳሌ", "ተጨማሪ",
}
WORD_RE = re.compile(r"[\u1200-\u137F]+|[a-zA-Z]+")


def is_follow_up(message: str) -> bool:
    words = {w.lower() for w in WORD_RE.findall(message)}
    return bool(words & FOLLOW_UP_MARKERS)


class TutorService:
    def __init__(
        self,
        store: ChunkStore,
        provider: AIProvider,
        relevance_threshold: float = 0.35,
        db: Optional[Any] = None,
    ):
        self.store = store
        self.provider = provider
        self.low_confidence = relevance_threshold
        self.db = db
        self._reload_lock = threading.Lock()
        self._index_version = -1
        self._index = BM25Index([])
        self.kb_version = ""
        self.reload()

    @property
    def indexed_chunks(self) -> int:
        return len(self._index)

    @property
    def index(self) -> BM25Index:
        return self._index

    def reload(self) -> None:
        """Rebuild the index from disk and swap it in; in-flight requests keep the old one."""
        with self._reload_lock:
            version = self.store.version
            chunks = self.store.load()
            self._index = BM25Index(chunks)
            self.kb_version = compute_kb_version(chunks)
            self._index_version = version

    def _refresh_if_changed(self) -> None:
        # Another worker process may have ingested a course; one stat() call detects it.
        if self.store.version != self._index_version:
            self.reload()

    def answer(self, request: ChatRequest) -> ChatResponse:
        self._refresh_if_changed()
        index = self._index
        # Manual UI override wins; otherwise script + marker-word detection picks the language.
        detection = detect_language_with_confidence(request.message, request.language)
        language = detection.code

        # Conversational context: from request payload or database session history
        history: List[ConversationTurn] = list(request.history)
        if not history and self.db:
            history = self.db.get_recent_turns(request.session)

        # First attempt: search with current query
        result = index.retrieve(request.message, TOP_K, request.scope, request.lesson)
        confidence = result.top_confidence

        # Context-aware expansion for follow-up questions
        if confidence < HIGH_CONFIDENCE and history and is_follow_up(request.message):
            last_user_turn = next((t.content for t in reversed(history) if t.role == "user"), "")
            if last_user_turn and last_user_turn.strip().lower() != request.message.strip().lower():
                expanded_result = index.retrieve(f"{last_user_turn} {request.message}", TOP_K, request.scope, request.lesson)
                prior_result = index.retrieve(last_user_turn, TOP_K, request.scope, request.lesson)
                candidates = [r for r in (expanded_result, prior_result) if r.passages]
                if candidates:
                    best = max(candidates, key=lambda r: r.top_confidence)
                    if best.top_confidence > confidence:
                        result = best
                        confidence = best.top_confidence

        if confidence >= HIGH_CONFIDENCE:
            selected = [p for p in result.passages if p.confidence >= self.low_confidence]
            return self._attach_language(
                self._generate(request, selected, language, confidence, history=history), detection
            )

        if result.query_terms and confidence < self.low_confidence:
            return self._attach_language(not_found_response(language, round(confidence, 3)), detection)

        wide = index.retrieve(request.message, WIDE_K, request.scope, request.lesson)
        selected = self._select_covering(wide)
        combined = wide.combined_confidence(selected)
        if selected and combined >= HIGH_CONFIDENCE:
            return self._attach_language(
                self._generate(request, selected, language, combined, history=history), detection
            )

        suggestions = [p.section for p in wide.passages[:MAX_SUGGESTIONS]] or \
            index.section_titles(request.scope, request.lesson)[:MAX_SUGGESTIONS]
        return self._attach_language(
            clarification_response(language, suggestions, round(combined, 3)), detection
        )

    @staticmethod
    def _attach_language(response: ChatResponse, detection) -> ChatResponse:
        response.language = detection.code
        response.language_confidence = round(detection.confidence, 3)
        response.language_overridden = detection.overridden
        return response

    @staticmethod
    def _select_covering(result: RetrievalResult) -> List[Passage]:
        """Greedily add passages while each one raises how much of the question is covered."""
        selected: List[Passage] = []
        best = 0.0
        for passage in result.passages:
            if len(selected) == TOP_K:
                break
            score = result.combined_confidence(selected + [passage])
            if score > best:
                selected.append(passage)
                best = score
        return selected

    def _generate(
        self,
        request: ChatRequest,
        passages: List[Passage],
        language: str,
        confidence: float,
        history: Optional[List[ConversationTurn]] = None,
    ):
        response = self.provider.generate(
            question=request.message,
            passages=passages,
            language=language,
            simple=request.simple,
            history=history,
        )
        if response.status == ChatStatus.ANSWERED:
            response.confidence = round(confidence, 3)
        return response
