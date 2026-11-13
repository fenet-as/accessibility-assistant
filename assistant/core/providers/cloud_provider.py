"""
Cloud AI Provider utilizing Google Gemini API.
Configured with strict zero-hallucination grounding prompts.
"""

import os
import re
from typing import List
from assistant.core.models import AIProvider, ChatResponse, ChatStatus, Citation, Passage

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class CloudProvider:
    name: str = "cloud_gemini"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        if GENAI_AVAILABLE and self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False
    ) -> ChatResponse:
        if not self.client or not GENAI_AVAILABLE:
            # Graceful degradation if API key is not supplied or library missing
            from assistant.core.providers.faq_provider import OfflineFAQProvider
            return OfflineFAQProvider().generate(question, passages, language, simple)

        context_text = "\n\n".join([
            f"[Source: {p.title} | Section: {p.section}]\n{p.text}"
            for p in passages
        ])

        system_instruction = (
            "You are an accessible, multilingual academic tutor for Ethiopian learners on the Savanna platform.\n"
            "STRICT GROUNDING RULES:\n"
            "1. Answer ONLY using the provided course passages below.\n"
            "2. If the answer cannot be directly derived from the passages, say: 'NOT_FOUND'. Do NOT invent or guess.\n"
            "3. Cite the exact section title you used.\n"
            f"4. Respond in {'Amharic' if language == 'am' else 'English'}.\n"
        )
        if simple:
            system_instruction += "5. SIMPLE MODE: Use short sentences, elementary vocabulary, and bullet points.\n"

        prompt = (
            f"COURSE PASSAGES:\n{context_text}\n\n"
            f"LEARNER QUESTION: {question}\n\n"
            "ANSWER:"
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1
                )
            )
            raw_text = response.text.strip() if response.text else ""

            if not raw_text or "NOT_FOUND" in raw_text:
                if language == "am":
                    msg = "ይቅርታ፣ ይህ ጥያቄ በተሰጠው የትምህርት ይዘት ውስጥ አልተገኘም። ከቀጥታ ረዳት ጋር መገናኘት ይፈልጋሉ?"
                else:
                    msg = "I'm sorry, but this question cannot be answered from the available course material. Would you like to connect with a human tutor?"
                return ChatResponse(
                    status=ChatStatus.NOT_FOUND,
                    language=language,
                    answer=msg,
                    citations=[],
                    actions=["get_human_help"]
                )

            citations = [
                Citation(title=p.title, section=p.section, url=p.url)
                for p in passages[:2]
            ]

            return ChatResponse(
                status=ChatStatus.ANSWERED,
                language=language,
                answer=raw_text,
                citations=citations,
                actions=["get_human_help"]
            )
        except Exception:
            # Fallback to offline FAQ if network or quota issue occurs
            from assistant.core.providers.faq_provider import OfflineFAQProvider
            return OfflineFAQProvider().generate(question, passages, language, simple)

