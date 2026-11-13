"""Tests for FastAPI REST Endpoints (Level 2 Integration)."""

import pytest
from fastapi.testclient import TestClient
from assistant.api.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "provider" in data
    assert data["indexed_chunks"] >= 6


def test_chat_endpoint_in_scope():
    payload = {
        "session": "test-session",
        "message": "What is shaping the future of virtual assistant work?",
        "language": "en"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "answered"
    assert len(data["citations"]) > 0


def test_chat_endpoint_out_of_scope():
    payload = {
        "session": "test-session",
        "message": "How do I bake a chocolate cake?",
        "language": "en"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_found"
    assert len(data["citations"]) == 0
    assert "get_human_help" in data["actions"]


def test_escalate_endpoint():
    payload = {
        "session": "test-session",
        "reason": "Need tutor help",
        "language": "en"
    }
    res = client.post("/api/escalate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "ticket_id" in data
    assert "meet.jit.si" in data["jitsi_room_url"]


def test_jobs_endpoint():
    res = client.get("/api/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) >= 2
    assert jobs[0]["@type"] == "JobPosting"
    assert "accommodationsOffered" in jobs[0]


def test_accommodations_endpoint():
    payload = {
        "job_id": "job-va-01",
        "accommodations": ["extra_time", "screen_reader_friendly"],
        "contact_channel": "telegram",
        "contact_value": "@testlearner"
    }
    res = client.post("/api/accommodations", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "received"

