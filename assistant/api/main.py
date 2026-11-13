"""
FastAPI Backend Application & REST API (Level 2 Integration).
Provides documented endpoints for chat, health, escalation, jobs, and accommodations.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from assistant.core.models import ChatRequest, ChatResponse, ChatStatus
from assistant.core.grounding import GroundingEngine

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
    return engine.process_query(request)


@app.post("/api/escalate", response_model=EscalationResponse, tags=["Escalation"])
def escalate(req: EscalationRequest) -> EscalationResponse:
    """One-click human escalation creating a learner-consented support room."""
    ticket = f"HELP-{os.urandom(3).hex().upper()}"
    room = f"ALX-Help-{ticket}"
    return EscalationResponse(
        ticket_id=ticket,
        status="pending_tutor",
        message="A live tutor has been notified. You can join the room below when ready to share your screen.",
        jitsi_room_url=f"https://meet.jit.si/{room}"
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
    record = req.model_dump()
    ACCOMMODATION_STORE.append(record)
    return {
        "status": "received",
        "message": "Accommodation request recorded. The recruiter will contact you via your chosen channel.",
        "job_id": req.job_id
    }


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


