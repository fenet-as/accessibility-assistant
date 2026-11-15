"""Routes each question to Gemini first; FAQ is the grounded fallback."""

from __future__ import annotations

from typing import List, Optional

from assistant.domain.models import ChatResponse, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.infrastructure.providers.routing import prefers_extractive_answer
from assistant.infrastructure.usage import UsageTracker

_DEFAULT_HIGH_CONFIDENCE = 0.6


class RoutedAIProvider:
    """Cloud mode: Gemini primary, FAQ only when generative fails or extractive is forced."""

    name: str = "routed_cloud"

    def __init__(
        self,
        faq: AIProvider,
        generative: AIProvider,
        *,
        usage: Optional[UsageTracker] = None,
        high_confidence: float = _DEFAULT_HIGH_CONFIDENCE,
        prefer_extractive: bool = False,
    ):
        self.faq = faq
        self.generative = generative
        self.usage = usage
        self.high_confidence = high_confidence
        self.prefer_extractive = prefer_extractive

    def provider_status(self) -> dict:
        generative = {}
        if hasattr(self.generative, "provider_status"):
            generative = self.generative.provider_status()
        return {
            "name": self.name,
            "prefer_extractive": self.prefer_extractive,
            "generative": generative,
            "fallback": getattr(self.faq, "name", "offline_faq"),
        }

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
        history: Optional[List[ConversationTurn]] = None,
        *,
        confidence: float = 0.0,
        answer_mode: str = "course",
        scope_confirmed: bool = True,
    ) -> ChatResponse:
        # Extractive FAQ is only useful when course passages exist.
        if (
            answer_mode != "general"
            and passages
            and self.prefer_extractive
            and prefers_extractive_answer(
                question,
                passages,
                confidence=confidence,
                simple=simple,
                history=history,
                high_confidence=self.high_confidence,
            )
        ):
            response = self.faq.generate(
                question, passages, language, simple, history=history, confidence=confidence,
                answer_mode=answer_mode, scope_confirmed=scope_confirmed,
            )
            response.provider = self.faq.name
            response.answer_source = response.answer_source or "faq"
            response.fallback_reason = response.fallback_reason or "extractive_preferred"
            if self.usage:
                self.usage.record_provider_request(self.faq.name)
                self.usage.record_fallback("extractive_preferred")
            return response

        response = self.generative.generate(
            question, passages, language, simple, history=history, confidence=confidence,
            answer_mode=answer_mode, scope_confirmed=scope_confirmed,
        )
        # GeminiProvider already falls back to FAQ with fallback_reason set.
        if not response.provider:
            response.provider = getattr(response, "provider", None) or self.generative.name
        if not response.answer_source:
            response.answer_source = (
                "cloud" if self.generative.name == "cloud_gemini" else "local"
            )
        if self.usage and response.answer_source in ("cloud", "cloud_general"):
            self.usage.record_provider_request(self.generative.name)
        return response
