from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from assistant.api.dependencies import get_container, get_sms_adapter, get_telegram_adapter
from assistant.api.schemas import AccommodationRequest, JobCreateRequest, SubscriptionRequest
from assistant.channels.sms import SMSAdapter
from assistant.channels.telegram import TelegramAdapter
from assistant.container import Container
from assistant.services.job_alerts import JobAlertDispatcher

router = APIRouter(prefix="/api", tags=["Career Gateway"])


@router.get("/jobs")
def list_jobs(container: Container = Depends(get_container)) -> List[Dict[str, Any]]:
    """Verified, non-expired job listings as schema.org/JobPosting JSON-LD."""
    return container.careers.list_jobs()


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    request: JobCreateRequest,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Accept a verified job listing; source_url is required."""
    try:
        job = container.careers.add_job(
            title=request.title,
            company_name=request.company_name,
            description=request.description,
            location=request.location,
            country=request.country,
            employment_type=request.employment_type,
            alternate_name=request.alternate_name,
            qualifications=request.qualifications,
            accommodations_offered=request.accommodations_offered,
            source_url=request.source_url,
            closing_date=request.closing_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "created", "job": job}


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Delete a job listing by ID."""
    removed = container.careers.delete_job(job_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {"status": "deleted", "job_id": job_id}


@router.post("/accommodations")
def submit_accommodation(
    request: AccommodationRequest,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Interview accommodation request. No medical proof or disability disclosure is asked for."""
    try:
        record_id = container.careers.request_accommodation(
            request.job_id, request.accommodations, request.contact_channel, request.contact_value
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    """Subscribe a Telegram chat or phone number to job alerts (consent required to receive)."""
    subscription_id = container.careers.subscribe(
        request.channel, request.contact, request.category, consent=request.consent
    )
    return {
        "status": "subscribed",
        "id": subscription_id,
        "consent": request.consent,
        "message": f"Successfully subscribed {request.contact} to job alerts via {request.channel}.",
    }


@router.post("/subscriptions/unsubscribe")
def unsubscribe_job_alerts(
    request: SubscriptionRequest,
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    removed = container.careers.unsubscribe(request.channel, request.contact)
    return {"status": "unsubscribed" if removed else "not_found", "removed": removed}


@router.post("/jobs/alerts/dispatch")
def dispatch_job_alerts(
    container: Container = Depends(get_container),
    telegram: TelegramAdapter = Depends(get_telegram_adapter),
    sms: SMSAdapter = Depends(get_sms_adapter),
) -> Dict[str, Any]:
    """On-demand dispatcher for consented subscribers (admin/demo)."""
    result = JobAlertDispatcher(container.careers, telegram=telegram, sms=sms).dispatch()
    return {"status": "ok", **result}
