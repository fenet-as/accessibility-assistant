"""Human escalation: one ticket and one Jitsi room per request, shared by every channel.

The learner opens the room and starts screen sharing themselves; nothing is shared automatically.
"""

import secrets

from assistant.domain.messages import ESCALATION_CREATED, localized
from assistant.domain.models import Escalation
from assistant.infrastructure.database import Database


class EscalationService:
    def __init__(self, db: Database, jitsi_base_url: str):
        self.db = db
        self.jitsi_base_url = jitsi_base_url.rstrip("/")

    def create(self, session_id: str, language: str = "en") -> Escalation:
        ticket_id = f"HELP-{secrets.token_hex(4).upper()}"
        # The room name is the only secret protecting the call, so it must not be guessable.
        room_url = f"{self.jitsi_base_url}/ALX-Help-{ticket_id}-{secrets.token_urlsafe(6)}"
        self.db.log_escalation(ticket_id, session_id, room_url)
        return Escalation(
            ticket_id=ticket_id,
            status="pending_tutor",
            message=localized(ESCALATION_CREATED, language),
            jitsi_room_url=room_url,
        )
