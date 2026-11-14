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
    ) -> ChatResponse:
        """Answer strictly from the retrieved passages, or return a not-found response."""
        ...
