"""Cloud provider backed by Google Gemini, with a strict grounding prompt.

Any failure (missing key or library, network, quota) degrades to the fallback provider,
so a learner never sees an error because of the cloud.
"""

import logging
from typing import List

from assistant.domain.language import get_language
from assistant.domain.messages import not_found_response
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, Passage
from assistant.domain.ports import AIProvider

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

NOT_FOUND_SENTINEL = "NOT_FOUND"
MAX_PASSAGES = 3
MAX_PASSAGE_CHARS = 1500


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


def build_prompt(question: str, passages: List[Passage], language: str) -> str:
    """Only the retrieved passages (at most MAX_PASSAGES, each trimmed) are sent, never the whole course."""
    blocks = []
    for p in passages[:MAX_PASSAGES]:
        body = p.text[:MAX_PASSAGE_CHARS]
        translated = (p.translations or {}).get(language)
        if translated:
            body = f"{translated}\n\n[Original course text]\n{body}"
        blocks.append(f"[Source: {p.title} | Section: {p.section}]\n{body}")
    context = "\n\n".join(blocks)
    return f"COURSE PASSAGES:\n{context}\n\nLEARNER QUESTION: {question}\n\nANSWER:"


def cited_passages(answer: str, passages: List[Passage]) -> List[Passage]:
    """Passages whose section title the model named; the top passage if it named none."""
    named = [p for p in passages[:MAX_PASSAGES] if p.section.lower() in answer.lower()]
    return named or passages[:1]


class GeminiProvider:
    name: str = "cloud_gemini"

    def __init__(self, api_key: str, model: str, fallback: AIProvider):
        self.model = model
        self.fallback = fallback
        self.client = genai.Client(api_key=api_key) if (genai and api_key) else None

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
    ) -> ChatResponse:
        if not self.client:
            return self.fallback.generate(question, passages, language, simple)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=build_prompt(question, passages, language),
                config=types.GenerateContentConfig(
                    system_instruction=build_system_instruction(language, simple),
                    temperature=0.1,
                ),
            )
        except Exception:
            logger.warning("Gemini call failed; using offline fallback", exc_info=True)
            return self.fallback.generate(question, passages, language, simple)

        text = (response.text or "").strip()
        if not text or NOT_FOUND_SENTINEL in text:
            return not_found_response(language)

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=text,
            citations=[p.to_citation() for p in cited_passages(text, passages)],
            actions=[HUMAN_HELP_ACTION],
        )
