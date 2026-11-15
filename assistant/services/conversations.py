"""Persistent chat conversations for the Savanna widget (device-owned, anonymous)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from assistant.infrastructure.database import Database

_TITLE_MAX = 60


def new_id(prefix: str = "c") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def title_from_message(message: str) -> str:
    text = " ".join((message or "").strip().split())
    if not text:
        return "New chat"
    if len(text) <= _TITLE_MAX:
        return text
    return text[: _TITLE_MAX - 1].rstrip() + "…"


def group_conversations(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Bucket conversations for the sidebar: today / yesterday / week / older."""
    now = datetime.now(timezone.utc).date()
    groups: Dict[str, List[Dict[str, Any]]] = {
        "today": [],
        "yesterday": [],
        "previous_7_days": [],
        "older": [],
    }
    for item in items:
        raw = item.get("updated_at") or item.get("created_at") or ""
        try:
            day = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
        except ValueError:
            groups["older"].append(item)
            continue
        delta = (now - day).days
        if delta <= 0:
            groups["today"].append(item)
        elif delta == 1:
            groups["yesterday"].append(item)
        elif delta <= 7:
            groups["previous_7_days"].append(item)
        else:
            groups["older"].append(item)
    return groups


class ConversationService:
    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        owner_id: str,
        *,
        course_id: str = "course:va-1",
        language: str = "auto",
        title: str = "New chat",
    ) -> Dict[str, Any]:
        owner_id = (owner_id or "").strip() or "anon"
        return self.db.create_conversation(
            new_id("conv"),
            owner_id,
            title=title,
            course_id=course_id or "course:va-1",
            language=language or "auto",
        )

    def list_for_owner(self, owner_id: str, *, q: str = "", limit: int = 100) -> Dict[str, Any]:
        owner_id = (owner_id or "").strip() or "anon"
        items = self.db.list_conversations(owner_id, limit=limit, q=q)
        return {"conversations": items, "groups": group_conversations(items)}

    def get(self, conversation_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        conv = self.db.get_conversation(conversation_id, owner_id)
        if not conv:
            return None
        messages = self.db.list_messages(conversation_id, owner_id)
        return {**conv, "messages": messages}

    def rename(self, conversation_id: str, owner_id: str, title: str) -> Optional[Dict[str, Any]]:
        if not self.db.rename_conversation(conversation_id, owner_id, title):
            return None
        return self.db.get_conversation(conversation_id, owner_id)

    def delete(self, conversation_id: str, owner_id: str) -> bool:
        return self.db.delete_conversation(conversation_id, owner_id)

    def append_user_message(
        self,
        conversation_id: str,
        owner_id: str,
        content: str,
        *,
        language: str = "",
    ) -> Optional[Dict[str, Any]]:
        conv = self.db.get_conversation(conversation_id, owner_id)
        if not conv:
            return None
        msg = self.db.add_message(
            new_id("msg"),
            conversation_id,
            "user",
            content,
            language=language,
        )
        # Auto-title from the first user message when still default.
        if (conv.get("title") or "").strip() in ("", "New chat"):
            self.db.rename_conversation(conversation_id, owner_id, title_from_message(content))
        return msg

    def append_assistant_message(
        self,
        conversation_id: str,
        owner_id: str,
        content: str,
        *,
        language: str = "",
        provider: str = "",
        answer_source: str = "",
        source_type: str = "",
        cache_hit: bool = False,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.db.get_conversation(conversation_id, owner_id):
            return None
        return self.db.add_message(
            new_id("msg"),
            conversation_id,
            "assistant",
            content,
            language=language,
            provider=provider,
            answer_source=answer_source,
            source_type=source_type,
            cache_hit=cache_hit,
            citations=citations,
            metadata=metadata,
        )
