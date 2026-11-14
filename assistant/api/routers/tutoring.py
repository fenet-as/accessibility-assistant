import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from assistant.api.dependencies import get_container
from assistant.api.schemas import EscalationRequest
from assistant.container import Container
from assistant.domain.models import ChatRequest, ChatResponse, Escalation

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse, tags=["Tutoring"])
def chat(
    request: ChatRequest,
    background: BackgroundTasks,
    container: Container = Depends(get_container),
) -> ChatResponse:
    """Ask a question; answers come only from course content, with citations."""
    response = container.tutor.answer(request)
    background.add_task(container.analytics.record_question, request, response)
    return response


@router.post("/chat/stream", tags=["Tutoring"])
def chat_stream(
    request: ChatRequest,
    background: BackgroundTasks,
    container: Container = Depends(get_container),
) -> StreamingResponse:
    """Single-chunk SSE stream for clients that want progressive UI without changing grounding rules."""

    def event_stream():
        response = container.tutor.answer(request)
        background.add_task(container.analytics.record_question, request, response)
        payload = json.loads(response.model_dump_json())
        yield f"data: {json.dumps(payload)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/escalate", response_model=Escalation, tags=["Escalation"])
def escalate(request: EscalationRequest, container: Container = Depends(get_container)) -> Escalation:
    """One-click human help: creates a ticket and a room the learner joins when ready."""
    return container.escalations.create(request.session, request.language)
