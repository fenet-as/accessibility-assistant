"""Teacher analytics: anonymous question logging and aggregate summaries."""

from typing import Any, Dict

from assistant.domain.models import ChatRequest, ChatResponse
from assistant.infrastructure.database import Database

UNRESOLVED_TOPIC = "unresolved"


class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db

    def record_question(self, request: ChatRequest, response: ChatResponse) -> None:
        self.db.log_query(
            session_id=request.session,
            message=request.message,
            language=response.language,
            status=response.status.value,
            topic=response.citations[0].section if response.citations else UNRESOLVED_TOPIC,
            mode=request.mode,
        )

    def summary(self) -> Dict[str, Any]:
        return self.db.analytics_summary()
