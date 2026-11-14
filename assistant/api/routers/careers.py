from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from assistant.api.dependencies import get_container
from assistant.api.schemas import AccommodationRequest, SubscriptionRequest
from assistant.container import Container

router = APIRouter(prefix="/api", tags=["Career Gateway"])


@router.get("/jobs")
def list_jobs(container: Container = Depends(get_container)) -> List[Dict[str, Any]]:
    """Job listings as schema.org/JobPosting JSON-LD."""
    return container.careers.list_jobs()


@router.post("/accommodations")
def submit_accommodation(
    request: AccommodationRequest,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Interview accommodation request. No medical proof or disability disclosure is asked for."""
    record_id = container.careers.request_accommodation(
        request.job_id, request.accommodations, request.contact_channel, request.contact_value
    )
    return {
        "status": "received",
        "id": record_id,
        "message": "Accommodation request recorded. The recruiter will contact you via your chosen channel.",
        "job_id": request.job_id,
    }


@router.post("/subscriptions")
def subscribe_job_alerts(
    request: SubscriptionRequest,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Subscribe a Telegram chat or phone number to job alerts."""
    subscription_id = container.careers.subscribe(request.channel, request.contact, request.category)
    return {
        "status": "subscribed",
        "id": subscription_id,
        "message": f"Successfully subscribed {request.contact} to job alerts via {request.channel}.",
    }
