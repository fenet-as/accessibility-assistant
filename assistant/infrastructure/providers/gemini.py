"""Cloud provider backed by Google Gemini, with a strict grounding prompt.

Any failure (missing key or library, network, quota) degrades to the fallback provider,
so a learner never sees an error because of the cloud.
"""

import logging
from typing import List

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
MAX_CITATIONS = 2


def build_system_instruction(language: str, simple: bool) -> str:
    rules = [
        "You are an accessible, multilingual academic tutor for Ethiopian learners on the Savanna platform.",
        "STRICT GROUNDING RULES:",
        "1. Answer ONLY using the provided course passages below.",
        f"2. If the answer cannot be directly derived from the passages, say: '{NOT_FOUND_SENTINEL}'. "
        "Do NOT invent or guess.",
        "3. Cite the exact section title you used.",
        f"4. Respond in {'Amharic' if language == 'am' else 'English'}.",
    ]
    if simple:
        rules.append("5. SIMPLE MODE: Use short sentences, elementary vocabulary, and bullet points.")
    return "\n".join(rules)


def build_prompt(question: str, passages: List[Passage]) -> str:
    context = "\n\n".join(f"[Source: {p.title} | Section: {p.section}]\n{p.text}" for p in passages)
    return f"COURSE PASSAGES:\n{context}\n\nLEARNER QUESTION: {question}\n\nANSWER:"


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
                contents=build_prompt(question, passages),
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
            citations=[p.to_citation() for p in passages[:MAX_CITATIONS]],
            actions=[HUMAN_HELP_ACTION],
        )
