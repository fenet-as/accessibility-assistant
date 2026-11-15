"""REST API for persistent Savanna chat conversations (device-owned)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from assistant.api.dependencies import get_container
from assistant.container import Container

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


def _owner(x_owner_id: Optional[str]) -> str:
    owner = (x_owner_id or "").strip()
    if not owner or len(owner) > 128:
        raise HTTPException(status_code=400, detail="X-Owner-Id header required (device id)")
    return owner


class CreateConversationBody(BaseModel):
    course_id: str = "course:va-1"
    language: str = "auto"
    title: str = "New chat"


class RenameBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class AppendMessagesBody(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=2000)
    assistant_message: str = Field(default="", max_length=20000)
    language: str = ""
    provider: str = ""
    answer_source: str = ""
    source_type: str = ""
    cache_hit: bool = False
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("")
def create_conversation(
    body: CreateConversationBody,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    owner = _owner(x_owner_id)
    return container.conversations.create(
        owner, course_id=body.course_id, language=body.language, title=body.title
    )


@router.get("")
def list_conversations(
    q: str = "",
    limit: int = 100,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    owner = _owner(x_owner_id)
    return container.conversations.list_for_owner(owner, q=q, limit=min(limit, 200))


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    owner = _owner(x_owner_id)
    data = container.conversations.get(conversation_id, owner)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return data


@router.patch("/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    body: RenameBody,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    owner = _owner(x_owner_id)
    data = container.conversations.rename(conversation_id, owner, body.title)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return data


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, str]:
    owner = _owner(x_owner_id)
    if not container.conversations.delete(conversation_id, owner):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}


@router.post("/{conversation_id}/messages")
def append_turn(
    conversation_id: str,
    body: AppendMessagesBody,
    container: Container = Depends(get_container),
    x_owner_id: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Persist a user (+ optional assistant) turn after the chat API responds."""
    owner = _owner(x_owner_id)
    user = container.conversations.append_user_message(
        conversation_id, owner, body.user_message, language=body.language
    )
    if not user:
        raise HTTPException(status_code=404, detail="Conversation not found")
    assistant = None
    if body.assistant_message.strip():
        assistant = container.conversations.append_assistant_message(
            conversation_id,
            owner,
            body.assistant_message,
            language=body.language,
            provider=body.provider,
            answer_source=body.answer_source,
            source_type=body.source_type,
            cache_hit=body.cache_hit,
            citations=body.citations,
            metadata=body.metadata,
        )
    conv = container.conversations.get(conversation_id, owner)
    return {"user": user, "assistant": assistant, "conversation": conv}
