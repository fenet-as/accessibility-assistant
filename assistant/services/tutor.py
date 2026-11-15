"""Hybrid tutoring use case: classify the question, gather course evidence, then answer.

Retrieval confidence decides only whether course passages are used as evidence:
- High confidence (or several sections that together cover the question): course-grounded
  answer from the selected passages only, with citations.
- Otherwise there is no course evidence. That is not a refusal: in-scope questions go to the
  general-knowledge path, course-specific ones get a clarification or an honest "not in the
  course" reply, and off-topic ones get the course-scope policy reply.
Only the selected passages (never the whole course) reach the AI provider.
"""

import re
import threading
from dataclasses import dataclass
from typing import List, Optional

from assistant.domain.knowledge import compute_kb_version
from assistant.domain.language import detect_language, detect_language_with_confidence
from assistant.domain.messages import (
    clarification_response,
    course_choice_response,
    detect_social_response,
    not_found_response,
    out_of_scope_response,
    unclear_reference_response,
)
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.domain.source_meta import CONNECTIVITY_ONLINE, apply_response_meta
from assistant.config import Settings
from assistant.infrastructure.answer_cache import AnswerCache, history_fingerprint, is_cacheable
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers.answer_mode import COURSE, GENERAL
from assistant.infrastructure.retrieval import BM25Index, RetrievalResult
from assistant.infrastructure.session_history import SessionHistoryStore
from assistant.infrastructure.usage import UsageTracker
from assistant.services.course_matcher import CourseMatcher, CourseResolution
from assistant.services.question_classifier import (
    Classification,
    QuestionSignals,
    QuestionType,
    ScopePolicy,
    classify,
    parse_language_switch,
    read_signals,
    should_expand_follow_up,
    strip_course_meta,
    strip_language_switch,
)

__all__ = ["TutorService", "parse_language_switch", "should_expand_follow_up"]

TOP_K = 3
WIDE_K = 8
MAX_SUGGESTIONS = 3
HIGH_CONFIDENCE = 0.6

# Leading chitchat that hurts BM25 ("hey what is…") — strip before retrieval only.
_LEADING_SOCIAL = re.compile(
    r"^(hey|hi|hello|howdy|yo|sup|ok|okay|please|umm+|uh+|so)\b[\s,!.?\-]*",
    re.IGNORECASE,
)
_DEFINITION_INTENT = re.compile(
    r"\b(what is|what's|define|definition|meaning of)\b|ምንድን|ማለት ምን|ምን ማለት",
    re.IGNORECASE,
)
_TYPES_INTENT = re.compile(
    r"\b(how many|types?|categories|kinds?|classification)\b|በስንት|ስንት|ዓይነት|ክፍል|ይከፈላል",
    re.IGNORECASE,
)


def sanitize_retrieval_query(message: str) -> str:
    """Strip leading chitchat so BM25 sees the real question."""
    text = (message or "").strip()
    cleaned = _LEADING_SOCIAL.sub("", text).strip()
    return cleaned or text


# Common learner typos → course vocabulary (applied before BM25).
_COMMON_TYPOS = {
    "wher": "where",
    "freelancng": "freelancing",
    "freelanicng": "freelancing",
    "freelancingg": "freelancing",
    "freelancinig": "freelancing",
    "virutal": "virtual",
    "virtural": "virtual",
    "assitant": "assistant",
    "asistants": "assistants",
    "assistnat": "assistant",
    "remtoe": "remote",
    "remot": "remote",
    "cliant": "client",
    "cliants": "clients",
}


def _edit_distance_one(a: str, b: str) -> bool:
    """True when a and b differ by a single insert, delete, or substitution."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b, la, lb = b, a, lb, la
    # a is shorter or equal
    i = j = diffs = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        diffs += 1
        if diffs > 1:
            return False
        if la == lb:
            i += 1
            j += 1
        else:
            j += 1  # insertion in b
    if j < lb or i < la:
        diffs += 1
    return diffs <= 1


def soft_correct_query(message: str, vocabulary: Optional[set] = None) -> str:
    """Fix obvious English typos so retrieval can match course terms.

    Uses a small typo map first, then optional edit-distance-1 matches against
    the BM25 vocabulary for unknown tokens of length ≥ 4.

    Never rewrites stop words or tokens whose stemmed form is already indexed —
    otherwise "will"→"well" and "value"→"valu" corrupt well-formed questions.
    """
    from assistant.infrastructure.text_analysis import STOP_WORDS, analyze

    text = (message or "").strip()
    if not text:
        return text
    vocab = vocabulary or set()

    def fix_token(raw: str) -> str:
        lower = raw.lower()
        if lower in _COMMON_TYPOS:
            fixed = _COMMON_TYPOS[lower]
            return fixed if raw.islower() else fixed.capitalize() if raw[0].isupper() else fixed
        if lower in STOP_WORDS or lower in vocab or len(lower) < 4 or not lower.isalpha():
            return raw
        # Stemmed form already known to BM25 — leave the surface word alone.
        if any(term in vocab for term in analyze(lower, remove_stopwords=False)):
            return raw
        # Prefer course terms of similar length (±1).
        candidates = [
            term for term in vocab
            if term.isalpha() and abs(len(term) - len(lower)) <= 1 and _edit_distance_one(lower, term)
        ]
        if len(candidates) == 1:
            return candidates[0]
        return raw

    # Preserve non-word separators; only rewrite Latin alphabetic tokens.
    parts = re.split(r"([a-zA-Z]+)", text)
    return "".join(fix_token(p) if p.isalpha() else p for p in parts)


def _definition_topic(query: str) -> str:
    """Extract the topic after 'what is / define' for title matching."""
    text = (query or "").strip().lower()
    match = re.search(
        r"(?:what(?:'s| is| are)|define|definition of|meaning of)\s+(.+?)[\s?!.]*$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    topic = re.sub(r"^(a|an|the)\s+", "", match.group(1).strip())
    return topic.strip(" ?.!")


def _definition_boosted(passages: List[Passage], query: str) -> List[Passage]:
    """Prefer true definition sections for 'what is' asks — not future-of-industry essays."""
    if not passages or not _DEFINITION_INTENT.search(query or ""):
        return passages
    topic = _definition_topic(query)
    topic_terms = {t for t in re.findall(r"[a-z0-9]+", topic) if len(t) > 2}

    def score(p: Passage) -> float:
        section = (p.section or "").lower()
        lead = (getattr(p, "text", "") or "")[:280].lower()
        blob = f"{section} {lead}"
        bonus = 0.0
        # Strongest signal: section is itself a "What is …" definition heading.
        if section.startswith("what is") or "what is a " in section or "what is an " in section:
            bonus += 0.9
        if topic and topic in section:
            bonus += 0.7
        if topic_terms and topic_terms.issubset(set(re.findall(r"[a-z0-9]+", section))):
            bonus += 0.45
        # Lead sentence that defines the asked term (e.g. "What is freelancing? …").
        if topic and (lead.startswith("what is " + topic) or f"what is a {topic}" in lead[:80]):
            bonus += 0.6
        if "definition" in section:
            bonus += 0.35
        # Mild boost for real course intros — but not "Future of …" overview essays.
        if ("introduction" in section or "overview" in section) and "future" not in section:
            bonus += 0.15
        # Industry-future disambiguation notes ("can mean two different things") are NOT
        # the primary answer to "what is a virtual assistant?" / "what is freelancing?".
        if "future" in section:
            bonus -= 0.55
        if "two different things" in lead or ("can mean" in lead and "future" in section):
            bonus -= 0.45
        return (p.confidence or 0.0) + bonus

    return sorted(passages, key=score, reverse=True)


@dataclass
class CourseEvidence:
    passages: List[Passage]  # empty when nothing is strong enough to cite
    confidence: float  # best retrieval confidence seen: a signal, never a refusal reason
    suggestions: List[str]  # nearby section titles for clarification prompts


class TutorService:
    def __init__(
        self,
        store: ChunkStore,
        provider: AIProvider,
        relevance_threshold: float = 0.35,
        *,
        cache: Optional[AnswerCache] = None,
        usage: Optional[UsageTracker] = None,
        settings: Optional[Settings] = None,
        rate_limiter=None,
        careers=None,
        session_history: Optional[SessionHistoryStore] = None,
        course_matcher: Optional[CourseMatcher] = None,
    ):
        self.store = store
        self.provider = provider
        self.low_confidence = relevance_threshold
        self.cache = cache
        self.usage = usage
        self.settings = settings
        self.rate_limiter = rate_limiter
        self.careers = careers
        self.session_history = session_history or SessionHistoryStore()
        self.course_matcher = course_matcher or CourseMatcher(store)
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
            if self.course_matcher is not None:
                self.course_matcher.reload()

    def _refresh_if_changed(self) -> None:
        # Another worker process may have ingested a course; one stat() call detects it.
        if self.store.version != self._index_version:
            self.reload()

    @property
    def scope_policy(self) -> ScopePolicy:
        return ScopePolicy.parse(self.settings.course_scope_policy if self.settings else None)

    def answer(self, request: ChatRequest) -> ChatResponse:
        self._refresh_if_changed()
        index = self._index
        # Widget sends history; Telegram/SMS usually do not — fill from the session buffer.
        history: List[ConversationTurn] = list(request.history) or self.session_history.get(request.session)
        signals = read_signals(request.message, history)
        detection = self._detect_language(request, signals.language_switch)
        language = detection.code
        text_language = detect_language(request.message)

        # Greetings and job-listing requests never need course retrieval or an AI call.
        if signals.social or signals.job_listing:
            early = classify(
                signals, text_language=text_language, course_confidence=0.0, policy=self.scope_policy
            )
            if early.type == QuestionType.GREETING:
                social = detect_social_response(request.message, language)
                if social is not None:
                    return self._remember(request, self._finish(social, detection, early, request))
            if early.type == QuestionType.CAREER and self.careers:
                return self._remember(
                    request,
                    self._finish(self._job_listing_response(language), detection, early, request),
                )

        course_res = self._resolve_course(request, language)
        if course_res.ambiguous:
            suggestions = [
                f"{c.display_name} ({c.scope})"
                for c in course_res.candidates[:MAX_SUGGESTIONS]
            ] or self.course_matcher.known_scopes()
            return self._remember(
                request,
                self._finish(
                    course_choice_response(language, suggestions),
                    detection,
                    Classification(QuestionType.AMBIGUOUS),
                    request,
                    course_id=request.scope,
                ),
            )

        # Canonical scope for retrieval/citations; rewritten text for BM25 (typos / missing spaces).
        effective_scope = course_res.scope or request.scope
        retrieval_message = course_res.rewritten_message or request.message
        retrieval_message = self._expand_bare_course_query(retrieval_message, course_res)
        grounded_request = request.model_copy(
            update={"scope": effective_scope, "message": retrieval_message}
        )

        evidence = self._gather_evidence(index, grounded_request, signals, retrieval_message=retrieval_message)
        classification = classify(
            signals,
            text_language=text_language,
            course_confidence=evidence.confidence,
            policy=self.scope_policy,
            high_confidence=HIGH_CONFIDENCE,
            low_confidence=self.low_confidence,
        )
        qtype = classification.type
        confidence = round(evidence.confidence, 3)

        if qtype == QuestionType.AMBIGUOUS:
            suggestions = index.section_titles(effective_scope, request.lesson)[:MAX_SUGGESTIONS]
            return self._remember(
                request,
                self._finish(
                    unclear_reference_response(language, suggestions),
                    detection,
                    classification,
                    grounded_request,
                ),
            )
        if qtype == QuestionType.UNRELATED:
            return self._remember(
                request,
                self._finish(
                    out_of_scope_response(language, confidence),
                    detection,
                    classification,
                    grounded_request,
                ),
            )

        # Cache keys use client-supplied history only — session buffer must not block
        # identical standalone asks in Telegram/SMS from sharing a cache entry.
        client_history = list(request.history)

        if evidence.passages:
            # Gemini always gets the CURRENT question plus history; follow-ups depend on that history,
            # so their answers must not be served to a different conversation from the exact cache.
            response = self._generate(
                grounded_request,
                evidence.passages,
                language,
                evidence.confidence,
                history=history,
                cache_history=client_history,
                effective_query=retrieval_message,
                use_cache=qtype != QuestionType.FOLLOW_UP,
                answer_mode=COURSE,
                scope_confirmed=classification.scope_confirmed,
            )
            return self._remember(
                request,
                self._finish(response, detection, classification, grounded_request),
            )

        if qtype == QuestionType.COURSE:
            if evidence.confidence >= self.low_confidence:
                response = clarification_response(language, evidence.suggestions, confidence)
            else:
                response = not_found_response(language, confidence)
            return self._remember(
                request,
                self._finish(response, detection, classification, grounded_request),
            )

        # General / career / follow-up with no course evidence → Gemini general knowledge when online.
        response = self._generate(
            grounded_request,
            [],
            language,
            evidence.confidence,
            history=history,
            cache_history=client_history,
            effective_query=retrieval_message,
            use_cache=qtype != QuestionType.FOLLOW_UP,
            answer_mode=GENERAL,
            scope_confirmed=classification.scope_confirmed,
        )
        return self._remember(
            request,
            self._finish(response, detection, classification, grounded_request),
        )

    def _resolve_course(self, request: ChatRequest, language: str) -> CourseResolution:
        if self.course_matcher is None:
            return CourseResolution(
                scope=request.scope or "",
                display_name=request.scope or "",
                confidence=1.0,
                method="ui_scope",
                rewritten_message=request.message,
                ui_scope_honored=True,
            )
        return self.course_matcher.resolve(
            request.message,
            ui_scope=request.scope,
            language=language,
        )

    def _expand_bare_course_query(self, message: str, course_res: CourseResolution) -> str:
        """If the learner only named the course, ask 'what is …' so definition ranking applies."""
        if not message or not course_res.scope or not self.course_matcher:
            return message
        record = self.course_matcher.get(course_res.scope)
        if not record:
            return message
        from assistant.services.course_matcher import compact_course_text, normalize_course_text

        compact_msg = compact_course_text(message)
        phrases = [record.primary_search_phrase, record.canonical_name, *record.search_names, *record.aliases]
        for phrase in phrases:
            if phrase and compact_course_text(phrase) == compact_msg and len(compact_msg) >= 4:
                # Avoid double "what is what is …".
                if _DEFINITION_INTENT.search(message):
                    return message
                primary = record.primary_search_phrase or phrase
                return f"What is {primary}?"
        # "VA course" / "virtual assistant course" after rewrite may still be short.
        norm = normalize_course_text(message)
        if norm.endswith(" course") or norm.endswith(" training"):
            stem = norm.rsplit(" ", 1)[0]
            for phrase in phrases:
                if phrase and compact_course_text(phrase) == compact_course_text(stem):
                    primary = record.primary_search_phrase or phrase
                    return f"What is {primary}?"
        return message

    def _remember(self, request: ChatRequest, response: ChatResponse) -> ChatResponse:
        """Keep a short transcript so Telegram/SMS follow-ups work without client history."""
        if response.status == ChatStatus.ANSWERED and response.answer:
            self.session_history.append(request.session, request.message, response.answer)
        return response

    def _detect_language(self, request: ChatRequest, switch_lang: Optional[str]):
        # Manual UI override wins; language-switch intent next; else detect from text.
        detection = detect_language_with_confidence(request.message, switch_lang or request.language)
        if switch_lang:
            # Force the switched language even when the message text is English.
            detection.code = switch_lang
            detection.overridden = True
            detection.confidence = 1.0
        return detection

    def _job_listing_response(self, language: str) -> ChatResponse:
        # Job questions are answered only from verified SQLite jobs (never invented).
        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=self.careers.answer_job_question(language),
            citations=[],
            actions=[],
            confidence=1.0,
            answer_source="careers",
            provider="careers",
        )

    def _gather_evidence(
        self,
        index: BM25Index,
        request: ChatRequest,
        signals: QuestionSignals,
        *,
        retrieval_message: Optional[str] = None,
    ) -> "CourseEvidence":
        """Course passages strong enough to cite, plus the best retrieval confidence seen."""
        vocabulary = set(index._idf)
        source_message = retrieval_message if retrieval_message is not None else request.message

        def prepare(text: str) -> str:
            # Strip "hey/so/…" and fix obvious typos (wher → where) against the indexed vocabulary.
            return soft_correct_query(sanitize_retrieval_query(text), vocabulary)

        def run(query: str, k: int = TOP_K) -> RetrievalResult:
            return index.retrieve(query, k, request.scope, request.lesson)

        standalone = prepare(strip_language_switch(source_message) or source_message)
        prior = prepare(signals.prior_question) if signals.prior_question else ""
        intent_text = standalone
        definition_ask = bool(_DEFINITION_INTENT.search(standalone))
        # Definition asks need a wider candidate pool so "What is X?" sections are not
        # crowded out of TOP_K by "Future of … / Introduction & Overview" essays.
        primary_k = WIDE_K if definition_ask else TOP_K
        if signals.is_follow_up and signals.language_switch:
            # "Explain your previous answer in Amharic": the topic is the previous question.
            intent_text = prior
            candidates = [(prior, run(prior, primary_k))]
        elif signals.is_follow_up:
            extra = " types categories kinds how many" if _TYPES_INTENT.search(source_message) else ""
            expanded = f"{prior}{extra} {standalone}"
            candidates = [(expanded, run(expanded, primary_k)), (standalone, run(standalone, primary_k))]
        else:
            candidates = [(standalone, run(standalone, primary_k))]
            if signals.references_course:
                stripped = prepare(strip_course_meta(source_message))
                if stripped and stripped != standalone:
                    candidates.append((stripped, run(stripped, primary_k)))

        query, result = max(candidates, key=lambda c: c[1].top_confidence)
        confidence = result.top_confidence
        if signals.is_follow_up and not signals.language_switch and confidence < HIGH_CONFIDENCE:
            prior_result = run(prior, primary_k)
            if prior_result.top_confidence > confidence:
                # Ground in the prior topic's passages without pretending the follow-up itself scored high.
                query, result = prior, prior_result
                confidence = min(prior_result.top_confidence, HIGH_CONFIDENCE)

        if confidence >= HIGH_CONFIDENCE:
            selected = [p for p in result.passages if p.confidence >= self.low_confidence]
            ranked = _definition_boosted(selected, intent_text)
            return CourseEvidence(ranked[:TOP_K], confidence, [])

        suggestions: List[str] = []
        if result.query_terms and confidence >= self.low_confidence:
            wide = index.retrieve(query, WIDE_K, request.scope, request.lesson)
            selected = _definition_boosted(self._select_covering(wide), intent_text)
            combined = wide.combined_confidence(selected)
            if selected and combined >= HIGH_CONFIDENCE:
                return CourseEvidence(selected, combined, [])
            suggestions = [p.section for p in wide.passages[:MAX_SUGGESTIONS]]
        suggestions = suggestions or index.section_titles(request.scope, request.lesson)[:MAX_SUGGESTIONS]
        return CourseEvidence([], confidence, suggestions)

    @staticmethod
    def _finish(
        response: ChatResponse,
        detection,
        classification: Classification,
        request: Optional[ChatRequest] = None,
        *,
        course_id: Optional[str] = None,
    ) -> ChatResponse:
        response.language = detection.code
        response.language_confidence = round(detection.confidence, 3)
        response.language_overridden = detection.overridden
        response.question_type = classification.type.value
        return apply_response_meta(
            response,
            course_id=course_id if course_id is not None else (request.scope if request else response.course_id),
            connectivity=CONNECTIVITY_ONLINE,
        )

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

    def _model_version(self) -> str:
        if not self.settings:
            return self.provider.name
        if self.settings.ai_provider == "cloud":
            return f"cloud:{self.settings.gemini_model}"
        if self.settings.ai_provider == "local":
            return f"local:{self.settings.local_model_name}"
        return f"faq:{self.kb_version}"

    def _generate(
        self,
        request: ChatRequest,
        passages: List[Passage],
        language: str,
        confidence: float,
        history: Optional[List[ConversationTurn]] = None,
        cache_history: Optional[List[ConversationTurn]] = None,
        effective_query: Optional[str] = None,
        use_cache: bool = True,
        answer_mode: str = COURSE,
        scope_confirmed: bool = True,
    ):
        question = effective_query or request.message
        bypass_cache = bool(getattr(request, "regenerate", False))
        # Include answer mode so a course-grounded answer is never served for a general ask.
        model_version = f"{self._model_version()}|{answer_mode}"
        hist_fp = history_fingerprint(cache_history)
        cache_key = None
        if use_cache and self.cache and self.settings and self.settings.enable_exact_cache:
            cache_key = self.cache.make_key(
                scope=request.scope,
                language=language,
                question=question,
                simple=request.simple,
                kb_version=self.kb_version,
                model_version=model_version,
                history_fp=hist_fp,
            )
            # Regenerate skips the lookup but keeps the key so the fresh answer is stored.
            if not bypass_cache:
                cached = self.cache.get(cache_key)
                if cached:
                    if self.usage:
                        self.usage.record_cache_hit()
                    cached.confidence = round(confidence, 3)
                    return cached
                if self.usage:
                    self.usage.record_cache_miss()

        # Daily budget exhausted → FAQ-only path via provider fallback reason.
        if self.rate_limiter and self.rate_limiter.budget_exhausted():
            from assistant.infrastructure.providers.faq import OfflineFAQProvider

            faq_path = self.settings.faq_translations_path if self.settings else None
            faq = OfflineFAQProvider(faq_path if faq_path and faq_path.exists() else None)
            response = faq.generate(
                question=question,
                passages=passages,
                language=language,
                simple=request.simple,
                history=history,
                confidence=confidence,
                answer_mode=answer_mode,
                scope_confirmed=scope_confirmed,
            )
            response.fallback_reason = "budget"
            response.answer_source = "faq"
            if self.usage:
                self.usage.record_fallback("budget")
            return response

        wait_event = None
        is_leader = True
        if cache_key and self.rate_limiter:
            is_leader, wait_event = self.rate_limiter.acquire_inflight(cache_key)
            if not is_leader and wait_event is not None:
                wait_event.wait(timeout=30)
                if self.cache:
                    cached = self.cache.get(cache_key)
                    if cached:
                        if self.usage:
                            self.usage.record_cache_hit()
                        cached.confidence = round(confidence, 3)
                        return cached

        try:
            response = self.provider.generate(
                question=question,
                passages=passages,
                language=language,
                simple=request.simple,
                history=history,
                confidence=confidence,
                answer_mode=answer_mode,
                scope_confirmed=scope_confirmed,
            )
        finally:
            if cache_key and self.rate_limiter and is_leader:
                self.rate_limiter.release_inflight(cache_key)

        if response.status == ChatStatus.ANSWERED:
            response.confidence = round(confidence, 3)
            if cache_key and self.cache and is_cacheable(response, tuple(p.section for p in passages)):
                to_store = response.model_copy()
                to_store.cache_hit = False
                self.cache.set(
                    cache_key,
                    to_store,
                    question=question,
                    scope=request.scope,
                    kb_version=self.kb_version,
                    model_version=model_version,
                    history_fp=hist_fp,
                    answer_mode=answer_mode,
                )
        if self.rate_limiter:
            budget = self.rate_limiter.budget_snapshot()
            if budget["level"] == "warning":
                import logging

                logging.getLogger(__name__).warning("Daily AI budget at 90%%: %s", budget)
        return response
