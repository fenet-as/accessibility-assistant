"""Data schemas and protocols for the core assistant service."""

from enum import Enum
from typing import List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class ChatStatus(str, Enum):
    ANSWERED = "answered"
    NOT_FOUND = "not_found"
    NEEDS_HUMAN = "needs_human"


class Citation(BaseModel):
    title: str = Field(..., description="Document or course title")
    section: str = Field(..., description="Specific chapter or section heading")
    url: str = Field(..., description="Anchor link back to source content")


class Passage(BaseModel):
    id: str
    course: str
    title: str
    section: str
    anchor: str
    url: str
    text: str
    score: float = 0.0


class ChatRequest(BaseModel):
    session: str = Field(default="anon-session", description="Anonymous session identifier")
    message: str = Field(..., min_length=1, description="Learner question text")
    language: str = Field(default="auto", description="'am', 'en', or 'auto'")
    mode: str = Field(default="normal", description="'normal' or 'simple' (Plain-language)")
    scope: str = Field(default="course:va-1", description="Content scope to ground answers in")


class ChatResponse(BaseModel):
    status: ChatStatus = Field(..., description="Resolution status: answered | not_found | needs_human")
    language: str = Field(..., description="Response language: 'am' or 'en'")
    answer: str = Field(..., description="Grounded response text")
    citations: List[Citation] = Field(default_factory=list, description="Citations identifying the source")
    actions: List[str] = Field(default_factory=list, description="Suggested next actions, e.g. ['get_human_help']")


@runtime_checkable
class AIProvider(Protocol):
    name: str

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False
    ) -> ChatResponse:
        """Generate a grounded response strictly from retrieved passages."""
        ...

