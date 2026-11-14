"""Core entities shared by every layer. No framework or I/O code lives here."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

HUMAN_HELP_ACTION = "get_human_help"
CLARIFY_ACTION = "clarify"


class ChatStatus(str, Enum):
    ANSWERED = "answered"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_FOUND = "not_found"
    NEEDS_HUMAN = "needs_human"


class Citation(BaseModel):
    title: str = Field(..., description="Document or course title")
    section: str = Field(..., description="Specific chapter or section heading")
    url: str = Field(..., description="Anchor link back to source content")


class Passage(BaseModel):
    id: str
    scope: str = ""
    course: str
    lesson_id: str = ""
    title: str
    section: str
    anchor: str
    url: str
    text: str
    translations: Dict[str, str] = Field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    matched_terms: List[str] = Field(default_factory=list)

    def to_citation(self) -> Citation:
        return Citation(title=self.title, section=self.section, url=self.url)

    def text_in(self, language: str) -> Optional[str]:
        return self.translations.get(language) or (self.text if language == "en" else None)


class ConversationTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    session: str = Field(default="anon-session", description="Anonymous session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="Learner question text")
    language: str = Field(
        default="auto",
        description="Learner language override: en | am | ti | om | so | ar | auto",
    )
    mode: str = Field(default="normal", description="'normal' or 'simple' (plain language)")
    scope: str = Field(default="course:va-1", description="Course scope to ground answers in")
    lesson: Optional[str] = Field(default=None, description="Optional lesson id to restrict retrieval to")
    history: List[ConversationTurn] = Field(
        default_factory=list,
        description="Recent conversation turns from client localStorage for multi-turn contextual grounding",
    )

    @property
    def simple(self) -> bool:
        return self.mode == "simple"


class ChatResponse(BaseModel):
    status: ChatStatus = Field(..., description="answered | needs_clarification | not_found | needs_human")
    language: str = Field(..., description="Response language code (en|am|ti|om|so|ar)")
    answer: str = Field(..., description="Grounded response text")
    citations: List[Citation] = Field(default_factory=list, description="Sources of the answer")
    actions: List[str] = Field(default_factory=list, description="Suggested next actions")
    confidence: Optional[float] = Field(default=None, description="Retrieval confidence 0..1")
    suggestions: List[str] = Field(default_factory=list, description="Sections to choose from when unclear")
    language_confidence: Optional[float] = Field(
        default=None, description="How sure language detection was (1.0 when the learner overrode)"
    )
    language_overridden: bool = Field(
        default=False, description="True when the learner manually selected the response language"
    )
    translation_fallback: bool = Field(
        default=False,
        description="True when a curated translation was missing and the original course text was shown",
    )


class Escalation(BaseModel):
    ticket_id: str
    status: str
    message: str
    jitsi_room_url: str
