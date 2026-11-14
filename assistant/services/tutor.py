"""Grounded tutoring use case: retrieve, decide by confidence, then generate with citations.

- High confidence: answer from the retrieved passages only.
- Medium confidence: widen retrieval; answer if several sections together cover the question,
  otherwise ask the learner to clarify (with section suggestions).
- Low confidence: not_found, offering a human tutor.
Only the selected passages (never the whole course) reach the AI provider.
"""

import re
import threading
from typing import List, Optional

from assistant.domain.knowledge import compute_kb_version
from assistant.domain.language import detect_language_with_confidence
from assistant.domain.messages import clarification_response, not_found_response, detect_social_response
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.retrieval import BM25Index, RetrievalResult

TOP_K = 3
WIDE_K = 8
MAX_SUGGESTIONS = 3
HIGH_CONFIDENCE = 0.6

FOLLOW_UP_MARKERS = {
    # English demonstratives, pronouns and follow-up markers
    "that", "this", "these", "those", "it", "its", "they", "them", "their", "more",
    "example", "examples", "category", "categories", "type", "types", "kind", "kinds",
    "elaborate", "clarify", "detail", "details", "difference", "distinction", "which",
    "explain", "tell", "another",
    # Amharic demonstratives and follow-up markers
    "ይህ", "ይህን", "ያ", "ያንን", "እነዚህ", "እነዚያ", "ስለዚህ", "የበለጠ", "ማብራሪያ", "ምሳሌ", "ለምሳሌ", "ተጨማሪ", "ዓይነት", "ክፍል",
}
WORD_RE = re.compile(r"[\u1200-\u137F]+|[a-zA-Z]+")


def is_follow_up(message: str) -> bool:
    words = {w.lower() for w in WORD_RE.findall(message)}
    return bool(words & FOLLOW_UP_MARKERS) or len(words) <= 5


class TutorService:
    def __init__(self, store: ChunkStore, provider: AIProvider, relevance_threshold: float = 0.35):
        self.store = store
        self.provider = provider
        self.low_confidence = relevance_threshold
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

        # Short-circuit: greetings, farewells, and thanks don't need course retrieval.
        social = detect_social_response(request.message, language)
        if social is not None:
            return self._attach_language(social, detection)

        history: List[ConversationTurn] = list(request.history)

        result = index.retrieve(request.message, TOP_K, request.scope, request.lesson)
        confidence = result.top_confidence

        # Context-aware query expansion for follow-up questions
        effective_query = request.message
        if confidence < HIGH_CONFIDENCE and history and is_follow_up(request.message):
            last_user_turn = next((t.content for t in reversed(history) if t.role == "user"), "")
            if last_user_turn and last_user_turn.strip().lower() != request.message.strip().lower():
                expanded_query = f"{last_user_turn} {request.message}"
                expanded_result = index.retrieve(expanded_query, TOP_K, request.scope, request.lesson)
                prior_result = index.retrieve(last_user_turn, TOP_K, request.scope, request.lesson)

                if expanded_result.passages and expanded_result.top_confidence >= self.low_confidence:
                    result = expanded_result
                    confidence = expanded_result.top_confidence
                    effective_query = expanded_query
                elif prior_result.passages and prior_result.top_confidence > confidence:
                    result = prior_result
                    confidence = prior_result.top_confidence
                    effective_query = expanded_query

        if confidence >= HIGH_CONFIDENCE:
            selected = [p for p in result.passages if p.confidence >= self.low_confidence]
            return self._attach_language(
                self._generate(request, selected, language, confidence, history=history, effective_query=effective_query), detection
            )

        if result.query_terms and confidence < self.low_confidence:
            return self._attach_language(not_found_response(language, round(confidence, 3)), detection)

        wide = index.retrieve(effective_query, WIDE_K, request.scope, request.lesson)
        selected = self._select_covering(wide)
        combined = wide.combined_confidence(selected)
        if selected and combined >= HIGH_CONFIDENCE:
            return self._attach_language(
                self._generate(request, selected, language, combined, history=history, effective_query=effective_query), detection
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
        effective_query: Optional[str] = None,
    ):
        response = self.provider.generate(
            question=effective_query or request.message,
            passages=passages,
            language=language,
            simple=request.simple,
            history=history,
        )
        if response.status == ChatStatus.ANSWERED:
            response.confidence = round(confidence, 3)
        return response
