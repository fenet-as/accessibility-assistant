"""Interfaces the application layer depends on; infrastructure provides the implementations."""

from typing import List, Optional, Protocol, runtime_checkable

from assistant.domain.models import ChatResponse, ConversationTurn, Passage


@runtime_checkable
class AIProvider(Protocol):
    name: str

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
        """Answer from retrieved passages and/or general knowledge, per answer_mode."""
        ...
