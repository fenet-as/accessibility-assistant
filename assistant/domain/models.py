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
    OUT_OF_SCOPE = "out_of_scope"


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
    source_kind: str = "course"

    def to_citation(self) -> Citation:
        title = self.title
        if self.source_kind == "supplemental" and "Supplemental" not in title:
            title = f"{title} (Supplemental notes)"
        return Citation(title=title, section=self.section, url=self.url)

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
    regenerate: bool = Field(
        default=False,
        description="When true, bypass the exact-answer cache and produce a fresh response",
    )

    @property
    def simple(self) -> bool:
        return self.mode == "simple"


class ChatResponse(BaseModel):
    status: ChatStatus = Field(
        ..., description="answered | needs_clarification | not_found | needs_human | out_of_scope"
    )
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
    provider: Optional[str] = Field(default=None, description="AI backend that produced the answer (offline_faq, cloud_gemini, …)")
    cache_hit: bool = Field(default=False, description="True when the response was served from exact-answer cache")
    answer_source: Optional[str] = Field(
        default=None,
        description="cache | faq | cloud | cloud_general | local | social | none — how the answer was produced",
    )
    source_type: Optional[str] = Field(
        default=None,
        description=(
            "Learner-facing origin: course_grounded | general_knowledge | mixed | local_course | "
            "faq | cache | social | careers | none"
        ),
    )
    connectivity: Optional[str] = Field(
        default=None,
        description="online when served by the API; offline when answered from a local pack/cache",
    )
    course_id: Optional[str] = Field(
        default=None,
        description="Course scope the answer was grounded in (e.g. course:va-1)",
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description=(
            "Why FAQ was used instead of Gemini: "
            "timeout | error | server | auth | quota | citation_invalid | budget | unavailable"
        ),
    )
    question_type: Optional[str] = Field(
        default=None,
        description="greeting | course | general | follow_up | career | unrelated | ambiguous",
    )


class Escalation(BaseModel):
    ticket_id: str
    status: str
    message: str
    jitsi_room_url: str
