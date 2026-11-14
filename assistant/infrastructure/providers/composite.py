"""Routes each question to FAQ (extractive) or cloud/local generation."""

from __future__ import annotations

from typing import List, Optional

from assistant.domain.models import ChatResponse, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.infrastructure.providers.routing import prefers_extractive_answer
from assistant.infrastructure.usage import UsageTracker
_DEFAULT_HIGH_CONFIDENCE = 0.6


class RoutedAIProvider:
    """Cloud mode: FAQ-first, then Gemini when the question needs explanation."""

    name: str = "routed_cloud"

    def __init__(
        self,
        faq: AIProvider,
        generative: AIProvider,
        *,
        usage: Optional[UsageTracker] = None,
        high_confidence: float = _DEFAULT_HIGH_CONFIDENCE,
    ):
        self.faq = faq
        self.generative = generative
        self.usage = usage
        self.high_confidence = high_confidence

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
        if prefers_extractive_answer(
            question, passages, confidence=confidence, simple=simple, history=history,
            high_confidence=self.high_confidence,
        ):
            response = self.faq.generate(question, passages, language, simple, history=history)
            response.provider = self.faq.name
            response.answer_source = response.answer_source or "faq"
            if self.usage:
                self.usage.record_provider_request(self.faq.name)
            return response

        response = self.generative.generate(
            question, passages, language, simple, history=history, confidence=confidence
        )
        response.provider = getattr(response, "provider", None) or self.generative.name
        response.answer_source = response.answer_source or (
            "cloud" if self.generative.name == "cloud_gemini" else "local"
        )
        if self.usage:
            self.usage.record_provider_request(self.generative.name)
        return response