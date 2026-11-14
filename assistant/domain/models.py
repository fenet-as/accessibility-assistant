"""Core entities shared by every layer. No framework or I/O code lives here."""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field

HUMAN_HELP_ACTION = "get_human_help"


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

    def to_citation(self) -> Citation:
        return Citation(title=self.title, section=self.section, url=self.url)


class ChatRequest(BaseModel):
    session: str = Field(default="anon-session", description="Anonymous session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="Learner question text")
    language: str = Field(default="auto", description="'am', 'en', or 'auto'")
    mode: str = Field(default="normal", description="'normal' or 'simple' (plain language)")
    scope: str = Field(default="course:va-1", description="Course scope to ground answers in")

    @property
    def simple(self) -> bool:
        return self.mode == "simple"


class ChatResponse(BaseModel):
    status: ChatStatus = Field(..., description="answered | not_found | needs_human")
    language: str = Field(..., description="Response language: 'am' or 'en'")
    answer: str = Field(..., description="Grounded response text")
    citations: List[Citation] = Field(default_factory=list, description="Sources of the answer")
    actions: List[str] = Field(default_factory=list, description="Suggested next actions")


class Escalation(BaseModel):
    ticket_id: str
    status: str
    message: str
    jitsi_room_url: str
