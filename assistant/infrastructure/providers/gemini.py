"""Cloud provider backed by Google Gemini, with course-grounded and general-knowledge modes.

Any failure (missing key or library, network, quota) degrades to the FAQ fallback with an
explicit fallback_reason so the UI can label the answer honestly. Citations are taken only
from section titles the model actually named — never invented, never defaulted to the top hit.
"""

from __future__ import annotations

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import List, Optional

from assistant.domain.language import get_language
from assistant.domain.messages import not_found_response, out_of_scope_response
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.infrastructure.providers.answer_mode import (
    COURSE,
    GENERAL,
    GENERAL_HEADING,
    SENTINEL_NOT_FOUND,
    SENTINEL_OUT_OF_SCOPE,
)
from assistant.infrastructure.providers.gemini_availability import (
    GeminiAvailability,
    classify_gemini_failure,
    is_retryable_failure,
)
from assistant.infrastructure.token_budget import (
    estimate_tokens,
    trim_history_turns,
    trim_passages_for_context,
)
from assistant.infrastructure.usage import UsageTracker

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)

# Kept for older imports and LocalModelProvider.
NOT_FOUND_SENTINEL = SENTINEL_NOT_FOUND
MAX_PASSAGES = 3
_INPUT_COST_PER_M = 0.075
_OUTPUT_COST_PER_M = 0.30
_DEFAULT_TIMEOUT = 12.0


def build_system_instruction(
    language: str,
    simple: bool,
    *,
    answer_mode: str = COURSE,
    scope_confirmed: bool = True,
) -> str:
    lang = get_language(language)
    if answer_mode == GENERAL:
        rules = [
            "You are an accessible, multilingual academic tutor for Ethiopian learners on the Savanna platform.",
            "ANSWER MODE: GENERAL EDUCATIONAL KNOWLEDGE.",
            "1. No course passages were retrieved. Answer from your general knowledge.",
            "2. Do NOT invent course citations, section titles, lesson names, or pretend the answer "
            "comes from Savanna course material.",
            "3. Be clear and useful. Start with a direct answer, then a short explanation and one "
            "concrete example when helpful.",
            f"4. Respond in {lang.name_en} ({lang.name_native}). Honour any explicit language request.",
            "5. Use recent conversation context for follow-ups (pronouns like 'its', 'explain that'). "
            "Do not repeat the previous answer; answer the new ask.",
            "6. Stay within learning and career topics: virtual assistant work, freelancing, remote work, "
            "digital skills, courses, portfolios, job readiness and similar educational guidance.",
            f"7. If the question is clearly unrelated (sports scores, cooking recipes, random trivia, "
            f"medical advice, etc.), reply with exactly: '{SENTINEL_OUT_OF_SCOPE}'.",
            "8. Never claim you read a course page or cite a section that was not provided.",
        ]
        if not scope_confirmed:
            rules.append(
                "9. The classifier could not confirm this question is in scope. If it is not about "
                f"learning, careers, VA work, freelancing, remote work or digital skills, reply with "
                f"exactly: '{SENTINEL_OUT_OF_SCOPE}'."
            )
        if simple:
            rules.append("SIMPLE MODE: Use short sentences, elementary vocabulary, and bullet points.")
        return "\n".join(rules)

    rules = [
        "You are an accessible, multilingual academic tutor for Ethiopian learners on the Savanna platform.",
        "ANSWER MODE: COURSE-GROUNDED (with optional labeled general knowledge).",
        "1. Prefer the provided course passages (including any translation block) for course facts.",
        "2. Answer the CURRENT LEARNER QUESTION directly first. Give a clear definition when asked "
        "'what is …'. Do not answer with only industry-future speculation.",
        "3. Cite a course section ONLY when you used it. Write the exact section title. "
        "Never invent section titles. If you did not use a passage, do not cite one.",
        f"4. Respond in {lang.name_en} ({lang.name_native}). Honour any explicit language request.",
        "5. Never invent a translation of course content that is not already present in the passages. "
        "If a reliable translation is not in the passages, say so clearly and quote the original text.",
        "6. Preserve the original meaning of the course material. Do not rewrite the learner's intent.",
        "7. When the learner asks for another example, give a NEW concrete example (not a repeat). "
        "Never copy-paste your previous answer for a new follow-up.",
        f"8. If you add knowledge that is NOT in the passages, put it under a heading "
        f"'{GENERAL_HEADING}' and keep it clearly separate from course-grounded content. "
        "Do not present general knowledge as if it were course material.",
        "9. Use the recent conversation context for follow-ups (pronouns, 'explain that', "
        "'another example', 'how many types'). Resolve short follow-ups against the prior topic.",
        f"10. If the passages do not cover the question at all and you also cannot give a useful "
        f"educational explanation, reply with exactly: '{SENTINEL_NOT_FOUND}'.",
    ]
    if simple:
        rules.append("SIMPLE MODE: Use short sentences, elementary vocabulary, and bullet points.")
    return "\n".join(rules)


def build_prompt(
    question: str,
    passages: List[Passage],
    language: str,
    history: Optional[List[ConversationTurn]] = None,
    *,
    answer_mode: str = COURSE,
) -> str:
    """Only the retrieved passages are sent, never the whole course."""
    conversation_context = ""
    if history:
        turns = trim_history_turns(history)
        lines = [f"{'Learner' if t.role == 'user' else 'Tutor'}: {t.content}" for t in turns if t.content]
        if lines:
            conversation_context = "RECENT CONVERSATION CONTEXT:\n" + "\n".join(lines) + "\n\n"

    if answer_mode == GENERAL or not passages:
        return (
            f"{conversation_context}"
            f"CURRENT LEARNER QUESTION: {question}\n\n"
            "No course passages are available for this question.\n\nANSWER:"
        )

    blocks = []
    for passage in passages[:MAX_PASSAGES]:
        body = passage.text
        translated = (passage.translations or {}).get(language)
        if translated:
            body = f"{translated}\n\n[Original course text]\n{body}"
        blocks.append(f"[Source: {passage.title} | Section: {passage.section}]\n{body}")
    context = "\n\n".join(blocks)
    return f"COURSE PASSAGES:\n{context}\n\n{conversation_context}CURRENT LEARNER QUESTION: {question}\n\nANSWER:"


def cited_passages(answer: str, passages: List[Passage]) -> List[Passage]:
    """Passages whose section title the model named. Never invent a citation."""
    if not answer or not passages:
        return []
    lowered = answer.lower()
    named = [p for p in passages[:MAX_PASSAGES] if p.section and p.section.lower() in lowered]
    return named


def validate_citations(answer: str, passages: List[Passage]) -> bool:
    """True when every named citation belongs to the retrieved passages. Empty citations are allowed."""
    if not passages:
        return True
    allowed = {p.section.lower() for p in passages if p.section}
    cited = cited_passages(answer, passages)
    return all(p.section.lower() in allowed for p in cited)


class GeminiProvider:
    name: str = "cloud_gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback: AIProvider,
        *,
        max_context_tokens: int = 800,
        max_output_tokens: int = 250,
        max_chars_per_passage: int = 1500,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        usage: Optional[UsageTracker] = None,
    ):
        self.model = model
        self.fallback = fallback
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = max_output_tokens
        self.max_chars_per_passage = max_chars_per_passage
        self.timeout_seconds = timeout_seconds
        self.usage = usage
        self.client = genai.Client(api_key=api_key) if (genai and api_key) else None
        self.availability = GeminiAvailability(
            configured=bool((api_key or "").strip()),
            sdk_loaded=genai is not None,
            model=model,
        )

    def provider_status(self) -> dict:
        """Honest Gemini readiness — not the same as browser/internet connectivity."""
        return {"name": self.name, **self.availability.as_dict()}

    def _fallback(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool,
        history: Optional[List[ConversationTurn]],
        confidence: float,
        reason: str,
        *,
        answer_mode: str = COURSE,
        scope_confirmed: bool = True,
    ) -> ChatResponse:
        if self.usage:
            self.usage.record_fallback(reason)
            self.usage.record_provider_request(getattr(self.fallback, "name", "offline_faq"))
        response = self.fallback.generate(
            question,
            passages,
            language,
            simple,
            history=history,
            confidence=confidence,
            answer_mode=answer_mode,
            scope_confirmed=scope_confirmed,
        )
        response.fallback_reason = reason
        # Never claim Gemini generated this answer — fallback is FAQ/local only.
        response.answer_source = "faq"
        response.provider = getattr(self.fallback, "name", "offline_faq")
        if hasattr(response, "source_type"):
            response.source_type = "faq"
        return response

    def _call_gemini(self, system: str, prompt: str):
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.1,
                max_output_tokens=self.max_output_tokens,
            ),
        )

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
        history: Optional[List[ConversationTurn]] = None,
        *,
        confidence: float = 0.0,
        answer_mode: str = COURSE,
        scope_confirmed: bool = True,
    ) -> ChatResponse:
        mode = GENERAL if (answer_mode == GENERAL or not passages) else COURSE
        if not self.client:
            logger.warning("Gemini unavailable (missing key or SDK); using FAQ fallback")
            self.availability.mark_failure(
                "unavailable",
                "missing API key or google-genai SDK",
            )
            return self._fallback(
                question, passages, language, simple, history, confidence, "unavailable",
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )
        if self.availability.cooling_down():
            remaining = self.availability.seconds_remaining()
            logger.warning(
                "Gemini in quota cooldown for another %.0fs; using FAQ fallback without calling the API",
                remaining,
            )
            return self._fallback(
                question, passages, language, simple, history, confidence, "quota",
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )

        trimmed = trim_passages_for_context(
            passages,
            language,
            max_passages=MAX_PASSAGES,
            max_chars_per_passage=self.max_chars_per_passage,
            max_context_tokens=self.max_context_tokens,
        ) if passages else []
        system = build_system_instruction(
            language, simple, answer_mode=mode, scope_confirmed=scope_confirmed
        )
        prompt = build_prompt(question, trimmed, language, history=history, answer_mode=mode)
        input_tokens = estimate_tokens(system) + estimate_tokens(prompt)

        response = None
        started = time.perf_counter()
        for attempt in range(2):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self._call_gemini, system, prompt)
                    response = future.result(timeout=self.timeout_seconds)
                break
            except FuturesTimeout:
                logger.warning("Gemini timed out after %.1fs (attempt %s)", self.timeout_seconds, attempt + 1)
                if attempt == 0:
                    time.sleep(0.2 + random.random() * 0.3)
                    continue
                if self.usage:
                    self.usage.record_latency((time.perf_counter() - started) * 1000)
                self.availability.mark_failure("timeout", f"timeout after {self.timeout_seconds}s")
                return self._fallback(
                    question, passages, language, simple, history, confidence, "timeout",
                    answer_mode=mode, scope_confirmed=scope_confirmed,
                )
            except Exception as exc:
                reason, cooldown = classify_gemini_failure(exc)
                logger.warning(
                    "Gemini call failed (attempt %s, reason=%s): %s",
                    attempt + 1, reason, exc, exc_info=True,
                )
                if attempt == 0 and is_retryable_failure(reason):
                    time.sleep(0.3 + random.random() * 0.5)
                    continue
                if self.usage:
                    self.usage.record_latency((time.perf_counter() - started) * 1000)
                self.availability.mark_failure(reason, str(exc), cooldown_seconds=cooldown)
                return self._fallback(
                    question, passages, language, simple, history, confidence, reason,
                    answer_mode=mode, scope_confirmed=scope_confirmed,
                )

        latency_ms = (time.perf_counter() - started) * 1000
        if self.usage:
            self.usage.record_latency(latency_ms)
        self.availability.mark_success()

        text = (getattr(response, "text", None) or "").strip()
        output_tokens = estimate_tokens(text)
        cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M + (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
        if self.usage:
            self.usage.record_provider_request(self.name)
            self.usage.record_tokens(input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)

        if not text:
            return not_found_response(language)
        if SENTINEL_OUT_OF_SCOPE in text:
            return out_of_scope_response(language, round(confidence, 3) if confidence else None)
        if SENTINEL_NOT_FOUND in text:
            return not_found_response(language)

        citations = cited_passages(text, trimmed)
        if not validate_citations(text, trimmed):
            logger.warning("Gemini citations invalid; using FAQ fallback")
            return self._fallback(
                question, passages, language, simple, history, confidence, "citation_invalid",
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=text,
            citations=[p.to_citation() for p in citations],
            actions=[HUMAN_HELP_ACTION],
            provider=self.name,
            answer_source="cloud_general" if mode == GENERAL else "cloud",
        )
