"""Cloud provider backed by Google Gemini, with a strict grounding prompt.

Any failure (missing key or library, network, quota) degrades to the fallback provider,
so a learner never sees an error because of the cloud.
"""

import logging
from typing import List, Optional

from assistant.domain.language import get_language
from assistant.domain.messages import not_found_response
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
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

logger = logging.getLogger(__name__)

NOT_FOUND_SENTINEL = "NOT_FOUND"
MAX_PASSAGES = 3
# Rough Gemini flash pricing for hackathon dashboards (USD per 1M tokens).
_INPUT_COST_PER_M = 0.075
_OUTPUT_COST_PER_M = 0.30


def build_system_instruction(language: str, simple: bool) -> str:
    lang = get_language(language)
    rules = [
        "You are an accessible, multilingual academic tutor for Ethiopian learners on the Savanna platform.",
        "STRICT GROUNDING RULES:",
        "1. Answer ONLY using the provided course passages below (including any translation block).",
        f"2. If the answer cannot be directly derived from the passages, say: '{NOT_FOUND_SENTINEL}'. "
        "Do NOT invent or guess course facts.",
        "3. Cite the exact section title you used. Keep citation section titles unchanged.",
        f"4. Respond in {lang.name_en} ({lang.name_native}).",
        "5. Never invent a translation of course content that is not already present in the passages. "
        "If a reliable translation is not in the passages, say so clearly and quote the original text.",
        "6. Preserve the original meaning of the course material.",
    ]
    if simple:
        rules.append("7. SIMPLE MODE: Use short sentences, elementary vocabulary, and bullet points.")
    return "\n".join(rules)


def build_prompt(
    question: str,
    passages: List[Passage],
    language: str,
    history: Optional[List[ConversationTurn]] = None,
) -> str:
    """Only the retrieved passages are sent, never the whole course."""
    blocks = []
    for passage in passages[:MAX_PASSAGES]:
        body = passage.text
        translated = (passage.translations or {}).get(language)
        if translated:
            body = f"{translated}\n\n[Original course text]\n{body}"
        blocks.append(f"[Source: {passage.title} | Section: {passage.section}]\n{body}")
    context = "\n\n".join(blocks)

    conversation_context = ""
    if history:
        turns = trim_history_turns(history)
        lines = [f"{'Learner' if t.role == 'user' else 'Tutor'}: {t.content}" for t in turns if t.content]
        if lines:
            conversation_context = "RECENT CONVERSATION CONTEXT:\n" + "\n".join(lines) + "\n\n"

    return f"COURSE PASSAGES:\n{context}\n\n{conversation_context}CURRENT LEARNER QUESTION: {question}\n\nANSWER:"


def cited_passages(answer: str, passages: List[Passage]) -> List[Passage]:
    """Passages whose section title the model named; the top passage if it named none."""
    named = [p for p in passages[:MAX_PASSAGES] if p.section.lower() in answer.lower()]
    return named or passages[:1]


def validate_citations(answer: str, passages: List[Passage]) -> bool:
    cited = cited_passages(answer, passages)
    allowed = {p.section.lower() for p in passages}
    return bool(cited) and all(p.section.lower() in allowed for p in cited)


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
        usage: Optional[UsageTracker] = None,
    ):
        self.model = model
        self.fallback = fallback
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = max_output_tokens
        self.max_chars_per_passage = max_chars_per_passage
        self.usage = usage
        self.client = genai.Client(api_key=api_key) if (genai and api_key) else None

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
        history: Optional[List[ConversationTurn]] = None,
        *,
        confidence: float = 0.0,
    ) -> ChatResponse:
        if not self.client:
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence
            )

        trimmed = trim_passages_for_context(
            passages,
            language,
            max_passages=MAX_PASSAGES,
            max_chars_per_passage=self.max_chars_per_passage,
            max_context_tokens=self.max_context_tokens,
        )
        system = build_system_instruction(language, simple)
        prompt = build_prompt(question, trimmed, language, history=history)
        input_tokens = estimate_tokens(system) + estimate_tokens(prompt)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.1,
                    max_output_tokens=self.max_output_tokens,
                ),
            )
        except Exception:
            logger.warning("Gemini call failed; using offline fallback", exc_info=True)
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence
            )

        text = (response.text or "").strip()
        output_tokens = estimate_tokens(text)
        cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M + (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
        if self.usage:
            self.usage.record_provider_request(self.name)
            self.usage.record_tokens(input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)

        if not text or NOT_FOUND_SENTINEL in text:
            return not_found_response(language)

        citations = cited_passages(text, trimmed)
        if not validate_citations(text, trimmed):
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence
            )

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=text,
            citations=[p.to_citation() for p in citations],
            actions=[HUMAN_HELP_ACTION],
            provider=self.name,
            answer_source="cloud",
        )