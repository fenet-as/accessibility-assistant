"""
FastAPI Backend Application & REST API (Level 2 Integration).
Provides documented endpoints for chat, health, escalation, jobs, and accommodations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables from the single root .env file
_base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_base_dir / ".env", override=True)

from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

from assistant.core.models import ChatRequest, ChatResponse, ChatStatus
from assistant.core.grounding import GroundingEngine
from assistant.core.database import (
    log_query,
    add_subscription,
    add_accommodation,
    log_escalation,
    get_analytics_summary
)
from assistant.ingest.universal_chunker import UniversalChunker
from assistant.adapters.sms.service import SMSAdapter
from assistant.adapters.telegram.bot import TelegramAdapter

app = FastAPI(
    title="ALX Accessibility Assistant API",
    description="Multilingual, grounded AI tutor and Career Gateway API for Ethiopian learners.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-origin host embeds (Savanna, Job Portals)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = GroundingEngine()
sms_adapter = SMSAdapter()
telegram_adapter = TelegramAdapter()


class SMSInboundRequest(BaseModel):
    sender: str = Field(default="+251911000000", description="Originating phone number")
    body: str = Field(..., description="SMS message text")


class EscalationRequest(BaseModel):
    session: str = Field(default="anon-session")
    reason: str = Field(default="Need tutor assistance")
    language: str = Field(default="en")


class EscalationResponse(BaseModel):
    ticket_id: str
    status: str
    message: str
    jitsi_room_url: str


class AccommodationRequest(BaseModel):
    job_id: str = Field(..., description="Target job vacancy ID")
    accommodations: List[str] = Field(
        ...,
        description="e.g. ['extra_time', 'screen_reader_materials', 'accessible_venue']"
    )
    contact_channel: str = Field(..., description="e.g. 'telegram' or 'phone'")
    contact_value: str = Field(..., description="Handle or number")


# In-memory storage for hackathon MVP (no personal data retained)
ACCOMMODATION_STORE = []
SUBSCRIPTIONS_STORE = []


class SubscriptionRequest(BaseModel):
    channel: str = Field(..., description="'telegram' or 'sms'")
    contact: str = Field(..., description="Phone number or Telegram chat ID")
    category: str = Field(default="all", description="Job category preference")


class IngestRequest(BaseModel):
    course_id: str = Field(..., description="Unique course identifier, e.g. 'course:python-101'")
    course_title: str = Field(..., description="Human-readable course title, e.g. 'Python Foundations'")
    lesson_url: str = Field(default="/pages/lesson.html", description="Base lesson URL on LMS")
    content_type: str = Field(default="markdown", description="'markdown' or 'html'")
    content: str = Field(..., description="Raw text of the lesson in Markdown or HTML")


class IngestResponse(BaseModel):
    status: str
    course_id: str
    chunks_created: int
    sections: List[str]
    sample_url: str


@app.get("/api/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Health check endpoint exposing active provider and corpus size."""
    return {
        "status": "healthy",
        "provider": engine.provider.name,
        "indexed_chunks": len(engine.retriever.passages),
        "version": "1.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Tutoring"])
def chat(request: ChatRequest) -> ChatResponse:
    """Ask a question; returns strictly grounded answers with citations."""
    response = engine.process_query(request)
    log_query(
        session_id=request.session,
        message=request.message,
        language=response.language,
        status=response.status.value,
        topic=response.citations[0].section if response.citations else "unresolved",
        mode=request.mode
    )
    return response


@app.post("/api/escalate", response_model=EscalationResponse, tags=["Escalation"])
def escalate(req: EscalationRequest) -> EscalationResponse:
    """One-click human escalation creating a learner-consented support room."""
    ticket = f"HELP-{os.urandom(3).hex().upper()}"
    room = f"ALX-Help-{ticket}"
    room_url = f"https://meet.jit.si/{room}"
    log_escalation(ticket, req.session, room_url)
    return EscalationResponse(
        ticket_id=ticket,
        status="pending_tutor",
        message="A live tutor has been notified. You can join the room below when ready to share your screen.",
        jitsi_room_url=room_url
    )


@app.get("/api/jobs", tags=["Career Gateway"])
def list_jobs() -> List[Dict[str, Any]]:
    """List sample jobs formatted with schema.org/JobPosting JSON-LD."""
    return [
        {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "id": "job-va-01",
            "title": "Junior Virtual Assistant & Customer Support",
            "description": "Provide remote email management, scheduling, and customer communication using AI tools.",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "African Remote Operations"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Addis Ababa",
                    "addressCountry": "ET"
                }
            },
            "employmentType": "REMOTE",
            "qualifications": "Strong communication skills, familiarity with AI tools, English & Amharic fluency.",
            "accommodationsOffered": [
                "Flexible hours",
                "Screen reader friendly workflow",
                "Async text communication"
            ]
        },
        {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "id": "job-va-02",
            "title": "Digital Project Coordinator",
            "description": "Coordinate project deliverables, team check-ins, and documentation for international clients.",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "EthioTech Talent Hub"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Remote",
                    "addressCountry": "ET"
                }
            },
            "employmentType": "FULL_TIME",
            "qualifications": "Organization, attention to detail, digital tool fluency.",
            "accommodationsOffered": [
                "Screen reader accessible tools",
                "Interview accommodations upon request"
            ]
        }
    ]


@app.post("/api/accommodations", tags=["Career Gateway"])
def submit_accommodation(req: AccommodationRequest) -> Dict[str, Any]:
    """Submit interview accommodation request (privacy-preserving, no medical disclosure)."""
    rec_id = add_accommodation(req.job_id, req.accommodations, req.contact_channel, req.contact_value)
    return {
        "status": "received",
        "id": rec_id,
        "message": "Accommodation request recorded. The recruiter will contact you via your chosen channel.",
        "job_id": req.job_id
    }


@app.post("/api/subscriptions", tags=["Career Gateway"])
def subscribe_job_alerts(req: SubscriptionRequest) -> Dict[str, Any]:
    """Subscribe a channel (Telegram or SMS) to job alerts."""
    sub_id = add_subscription(req.channel, req.contact, req.category)
    return {
        "status": "subscribed",
        "id": sub_id,
        "message": f"Successfully subscribed {req.contact} to job alerts via {req.channel}."
    }


@app.get("/api/analytics/summary", tags=["Analytics"])
def analytics_summary() -> Dict[str, Any]:
    """Aggregated, privacy-preserving analytics summary (k-anonymity)."""
    return get_analytics_summary()


@app.get("/analytics", response_class=HTMLResponse, tags=["Analytics"])
def analytics_dashboard() -> HTMLResponse:
    """Interactive visual Teacher Analytics Dashboard."""
    path = Path(__file__).resolve().parent / "analytics.html"
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Analytics Dashboard Not Found</h1>")


@app.get("/api/lti/config.json", tags=["LTI 1.3 Standard"])
def lti_configuration() -> Dict[str, Any]:
    """1EdTech LTI 1.3 standard tool configuration manifest for Canvas/Moodle/Blackboard."""
    base_host = os.getenv("HOST_URL", "http://localhost:8000")
    return {
        "title": "ALX Accessibility Assistant & Tutor",
        "description": "Accessible multilingual AI tutor and career gateway module.",
        "oidc_initiation_url": f"{base_host}/api/lti/login",
        "target_link_uri": f"{base_host}/savanna/pages/concept-with-navigation.html",
        "extensions": [
            {
                "platform": "canvas.instructure.com",
                "privacy_level": "anonymous",
                "settings": {
                    "text": "ALX Tutor",
                    "placements": [
                        {"placement": "course_navigation", "message_type": "LtiResourceLinkRequest"}
                    ]
                }
            }
        ],
        "public_jwk_url": f"{base_host}/api/lti/jwks.json"
    }


@app.post("/api/lti/launch", tags=["LTI 1.3 Standard"])
def lti_launch(req: Dict[str, Any] = None) -> Dict[str, Any]:
    """LTI 1.3 OIDC launch endpoint simulating LMS authentication context."""
    return {
        "status": "authenticated",
        "standard": "LTI-1p3",
        "context": "VA-1: VA Foundations & Professional Identity",
        "redirect_url": "/savanna/pages/concept-with-navigation.html"
    }


@app.post("/api/sms/inbound", tags=["SMS Channel"])
async def sms_inbound(request: Request) -> Dict[str, Any]:
    """
    Universal 2-Way Inbound SMS endpoint.
    Accepts webhooks from Africa's Talking, Android GSM Gateway, Twilio, or direct JSON.
    Normalizes Ethiopian numbers (+2519... / +2517...) and dispatches replies automatically.
    """
    content_type = request.headers.get("content-type", "")
    sender = ""
    body = ""

    if "application/json" in content_type:
        try:
            data = await request.json()
            sender = data.get("sender") or data.get("from") or data.get("From") or ""
            body = data.get("body") or data.get("text") or data.get("message") or data.get("Body") or ""
        except Exception:
            pass
    else:
        # Form URL-encoded (Africa's Talking, Twilio, Android Gateway)
        try:
            from urllib.parse import parse_qs
            raw_bytes = await request.body()
            if raw_bytes:
                parsed = parse_qs(raw_bytes.decode("utf-8"))
                flat = {k.lower(): v[0] for k, v in parsed.items()}
                sender = flat.get("from") or flat.get("sender") or flat.get("phonenumber") or ""
                body = flat.get("text") or flat.get("body") or flat.get("message") or ""
        except Exception:
            pass

    # Fallback to query params if sent in GET/query
    if not sender:
        sender = request.query_params.get("from") or request.query_params.get("sender") or "+251911000000"
    if not body:
        body = request.query_params.get("text") or request.query_params.get("body") or "HELP"

    normalized_sender = sms_adapter.normalize_ethiopian_phone(str(sender))
    segments = sms_adapter.handle_inbound_sms(normalized_sender, str(body), dispatch_replies=True)

    return {
        "status": "success",
        "sender": normalized_sender,
        "segments": segments,
        "count": len(segments)
    }


@app.get("/sms-simulator", response_class=HTMLResponse, tags=["SMS Channel"])
def sms_simulator_view() -> HTMLResponse:
    """Interactive feature phone SMS simulator page for judges and offline demo."""
    sim_path = Path(__file__).resolve().parent.parent / "adapters" / "sms" / "simulator.html"
    if sim_path.exists():
        return HTMLResponse(content=sim_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SMS Simulator Not Found</h1>")


@app.get("/a11y-audit", response_class=HTMLResponse, tags=["System"])
def accessibility_audit_view() -> HTMLResponse:
    """Interactive axe-core Stage 1 accessibility gate audit runner."""
    audit_path = Path(__file__).resolve().parent.parent / "widget" / "audit.html"
    if audit_path.exists():
        return HTMLResponse(content=audit_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Audit Page Not Found</h1>")


@app.post("/api/telegram/webhook", tags=["Telegram Channel"])
async def telegram_webhook(update: Dict[str, Any]) -> Dict[str, Any]:
    """Webhook endpoint receiving updates from Telegram Bot API."""
    result = await telegram_adapter.handle_update(update)
    return {"status": "ok", "result": result}


# --- Course Ingestion & Curriculum Management Endpoints ---

@app.post("/api/admin/ingest", tags=["Course Ingestion"], response_model=IngestResponse)
def admin_ingest_course(req: IngestRequest):
    """
    Ingest new course material in Markdown or HTML.
    Automatically generates section anchors, bilingual keyword tags, and updates retrieval index.
    """
    try:
        chunker = UniversalChunker()
        chunks = chunker.ingest_course(
            course_id=req.course_id,
            course_title=req.course_title,
            content=req.content,
            content_type=req.content_type,
            lesson_url=req.lesson_url
        )
        # Reload the grounding engine's retriever so newly ingested chunks are active immediately
        engine.reload()
        return IngestResponse(
            status="success",
            course_id=req.course_id,
            chunks_created=len(chunks),
            sections=[c["section"] for c in chunks],
            sample_url=chunks[0]["url"] if chunks else req.lesson_url
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Course ingestion failed: {str(e)}")


@app.get("/api/admin/courses", tags=["Course Ingestion"])
def admin_list_courses() -> List[Dict[str, Any]]:
    """List all currently indexed courses, chunk counts, and section listings."""
    chunker = UniversalChunker()
    return chunker.list_courses()


@app.delete("/api/admin/courses/{course_id}", tags=["Course Ingestion"])
def admin_delete_course(course_id: str):
    """Delete a course and all its indexed chunks from the retrieval engine."""
    chunker = UniversalChunker()
    deleted = chunker.delete_course(course_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    engine.reload()
    return {"status": "deleted", "course_id": course_id}


@app.get("/admin/ingest", response_class=HTMLResponse, tags=["Course Ingestion"])
@app.get("/api/admin/ui", response_class=HTMLResponse, tags=["Course Ingestion"], include_in_schema=False)
def admin_ingest_view() -> HTMLResponse:
    """Accessible Web Portal for Course Curriculum Ingestion and Management."""
    path = Path(__file__).resolve().parent / "ingest.html"
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Ingest Portal Not Found</h1>", status_code=404)



# Mount Static Files for direct browser preview
base_dir = Path(__file__).resolve().parent.parent.parent
savanna_dir = base_dir / "savanna-static"
widget_dir = base_dir / "assistant" / "widget"

if widget_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(widget_dir)), name="widget")
    app.mount("/assistant/widget", StaticFiles(directory=str(widget_dir)), name="assistant_widget")

if savanna_dir.exists():
    app.mount("/savanna", StaticFiles(directory=str(savanna_dir), html=True), name="savanna")


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect home route directly to the active Savanna concept page."""
    return RedirectResponse(url="/savanna/pages/concept-with-navigation.html")


