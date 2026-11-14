from fastapi import APIRouter, BackgroundTasks, Depends

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


@router.post("/escalate", response_model=Escalation, tags=["Escalation"])
def escalate(request: EscalationRequest, container: Container = Depends(get_container)) -> Escalation:
    """One-click human help: creates a ticket and a room the learner joins when ready."""
    return container.escalations.create(request.session, request.language)
