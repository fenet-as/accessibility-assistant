"""Human escalation: one ticket and one Jitsi room per request, shared by every channel.

The learner opens the room and starts screen sharing themselves; nothing is shared automatically.
Staff are notified on Telegram when TELEGRAM_STAFF_CHAT_ID is configured.
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

import httpx

from assistant.domain.messages import ESCALATION_CREATED, localized
from assistant.domain.models import Escalation
from assistant.infrastructure.database import Database

logger = logging.getLogger(__name__)


class EscalationService:
    def __init__(
        self,
        db: Database,
        jitsi_base_url: str,
        *,
        telegram_bot_token: str = "",
        staff_chat_id: str = "",
    ):
        self.db = db
        self.jitsi_base_url = jitsi_base_url.rstrip("/")
        self.telegram_bot_token = telegram_bot_token
        self.staff_chat_id = staff_chat_id

    def create(self, session_id: str, language: str = "en", topic: str = "") -> Escalation:
        ticket_id = f"HELP-{secrets.token_hex(4).upper()}"
        # The room name is the only secret protecting the call, so it must not be guessable.
        room_url = f"{self.jitsi_base_url}/ALX-Help-{ticket_id}-{secrets.token_urlsafe(6)}"
        self.db.log_escalation(ticket_id, session_id, room_url, language=language, topic=topic, status="open")
        notified = self._notify_staff(ticket_id, language=language, topic=topic, room_url=room_url)
        message = localized(ESCALATION_CREATED, language)
        if not notified and self.staff_chat_id:
            message += " (Staff notification could not be delivered; please try again if no tutor joins.)"
        return Escalation(
            ticket_id=ticket_id,
            status="open",
            message=message,
            jitsi_room_url=room_url,
        )

    def claim(self, ticket_id: str, staff_id: str) -> Optional[Escalation]:
        if not self.db.update_escalation(ticket_id, status="assigned", assigned_to=staff_id):
            return None
        row = self.db.get_escalation(ticket_id)
        if not row:
            return None
        return Escalation(
            ticket_id=ticket_id,
            status="assigned",
            message=f"Ticket {ticket_id} claimed by {staff_id}.",
            jitsi_room_url=row["room_url"],
        )

    def close(self, ticket_id: str) -> Optional[Escalation]:
        if not self.db.update_escalation(ticket_id, status="closed"):
            return None
        row = self.db.get_escalation(ticket_id)
        if not row:
            return None
        return Escalation(
            ticket_id=ticket_id,
            status="closed",
            message=f"Ticket {ticket_id} closed.",
            jitsi_room_url=row["room_url"],
        )

    def _notify_staff(self, ticket_id: str, *, language: str, topic: str, room_url: str) -> bool:
        if not self.telegram_bot_token or not self.staff_chat_id:
            return False
        # Never include raw personal data — session ids are already hashed in DB.
        text = (
            f"New tutor request {ticket_id}\n"
            f"Language: {language}\n"
            f"Topic: {topic or 'n/a'}\n"
            f"Room: {room_url}\n"
            f"Claim with /claim {ticket_id}"
        )
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json={"chat_id": self.staff_chat_id, "text": text})
                if res.status_code != 200:
                    logger.warning("Staff Telegram notify failed: %s", res.status_code)
                    return False
                return True
        except httpx.HTTPError:
            logger.warning("Staff Telegram notify network error", exc_info=True)
            return False
