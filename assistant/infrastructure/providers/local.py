"""Optional self-hosted model provider (OpenAI-compatible HTTP). Falls back to offline FAQ."""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from assistant.domain.language import get_language
from assistant.domain.messages import not_found_response
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.domain.ports import AIProvider
from assistant.domain.messages import out_of_scope_response
from assistant.infrastructure.providers.answer_mode import (
    COURSE,
    GENERAL,
    SENTINEL_NOT_FOUND,
    SENTINEL_OUT_OF_SCOPE,
)
from assistant.infrastructure.providers.gemini import (
    build_prompt,
    build_system_instruction,
    cited_passages,
)
from assistant.infrastructure.token_budget import estimate_tokens, trim_passages_for_context
from assistant.infrastructure.usage import UsageTracker

logger = logging.getLogger(__name__)


class LocalModelProvider:
    name: str = "local_model"

    def __init__(
        self,
        base_url: str,
        model: str,
        fallback: AIProvider,
        *,
        max_context_tokens: int,
        max_output_tokens: int,
        timeout_seconds: float = 60.0,
        usage: Optional[UsageTracker] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = fallback
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.usage = usage

    def provider_status(self) -> dict:
        configured = bool(self.base_url)
        return {
            "name": self.name,
            "configured": configured,
            "available": configured,
            "status": "ready" if configured else "missing_url",
            "model": self.model,
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
        answer_mode: str = COURSE,
        scope_confirmed: bool = True,
    ) -> ChatResponse:
        mode = GENERAL if (answer_mode == GENERAL or not passages) else COURSE
        if not self.base_url:
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence,
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )

        trimmed = trim_passages_for_context(
            passages,
            language,
            max_context_tokens=self.max_context_tokens,
        ) if passages else []
        system = build_system_instruction(
            language, simple, answer_mode=mode, scope_confirmed=scope_confirmed
        )
        prompt = build_prompt(question, trimmed, language, history=history, answer_mode=mode)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": self.max_output_tokens,
        }
        input_tokens = estimate_tokens(system) + estimate_tokens(prompt)

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                res.raise_for_status()
                body = res.json()
        except Exception:
            logger.warning("Local model call failed; using offline FAQ fallback", exc_info=True)
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence,
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )

        text = ""
        try:
            text = (body["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError):
            return self.fallback.generate(
                question, passages, language, simple, history=history, confidence=confidence,
                answer_mode=mode, scope_confirmed=scope_confirmed,
            )

        output_tokens = estimate_tokens(text)
        if self.usage:
            self.usage.record_provider_request(self.name)
            self.usage.record_tokens(input_tokens=input_tokens, output_tokens=output_tokens)

        if not text:
            return not_found_response(language)
        if SENTINEL_OUT_OF_SCOPE in text:
            return out_of_scope_response(language)
        if SENTINEL_NOT_FOUND in text:
            return not_found_response(language)

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=text,
            citations=[p.to_citation() for p in cited_passages(text, trimmed)],
            actions=[HUMAN_HELP_ACTION],
            provider=self.name,
            answer_source="local",
        )