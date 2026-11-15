"""Anonymous analytics: question outcomes without unnecessary personal content."""

from __future__ import annotations

import re
from typing import Any, Dict

from assistant.domain.models import ChatRequest, ChatResponse
from assistant.infrastructure.database import Database

UNRESOLVED_TOPIC = "unresolved"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
_PHONE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")


def redact_question(text: str, mode: str = "redacted") -> str:
    if mode == "off":
        return ""
    if mode != "redacted":
        return text
    cleaned = _EMAIL.sub("[email]", text or "")
    cleaned = _PHONE.sub("[phone]", cleaned)
    return cleaned


class AnalyticsService:
    def __init__(self, db: Database, log_question_text: str = "redacted"):
        self.db = db
        self.log_question_text = log_question_text

    def record_question(self, request: ChatRequest, response: ChatResponse) -> None:
        self.db.log_query(
            session_id=request.session,
            message=redact_question(request.message, self.log_question_text),
            language=response.language,
            status=response.status.value,
            topic=response.citations[0].section if response.citations else UNRESOLVED_TOPIC,
            mode=request.mode,
        )

    def summary(self) -> Dict[str, Any]:
        return self.db.analytics_summary()
