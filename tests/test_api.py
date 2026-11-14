"""REST endpoints (Level 2 integration)."""

from dataclasses import replace

from fastapi.testclient import TestClient

from assistant.api.app import create_app
from assistant.container import build_container


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["provider"] == "offline_faq"
    assert data["indexed_chunks"] >= 6


def test_chat_endpoint_in_scope(client):
    res = client.post("/api/chat", json={
        "session": "test-session",
        "message": "What is shaping the future of virtual assistant work?",
        "language": "en",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "answered"
    assert len(data["citations"]) > 0


def test_chat_endpoint_out_of_scope(client):
    res = client.post("/api/chat", json={
        "session": "test-session",
        "message": "How do I bake a chocolate cake?",
        "language": "en",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_found"
    assert data["citations"] == []
    assert "get_human_help" in data["actions"]


def test_chat_rejects_oversized_message(client):
    res = client.post("/api/chat", json={"message": "x" * 5000})
    assert res.status_code == 422


def test_escalate_endpoint(client):
    res = client.post("/api/escalate", json={"session": "test-session", "reason": "Need tutor help"})
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_id"].startswith("HELP-")
    assert data["jitsi_room_url"].startswith("https://meet.jit.si/ALX-Help-")


def test_escalation_rooms_are_unique(client):
    urls = {client.post("/api/escalate", json={}).json()["jitsi_room_url"] for _ in range(5)}
    assert len(urls) == 5


def test_jobs_endpoint(client):
    res = client.get("/api/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) >= 2
    assert jobs[0]["@type"] == "JobPosting"
    assert "accommodationsOffered" in jobs[0]


def test_accommodations_endpoint(client):
    res = client.post("/api/accommodations", json={
        "job_id": "job-va-01",
        "accommodations": ["extra_time", "screen_reader_friendly"],
        "contact_channel": "telegram",
        "contact_value": "@testlearner",
    })
    assert res.status_code == 200
    assert res.json()["status"] == "received"


def test_subscriptions_endpoint(client):
    res = client.post("/api/subscriptions", json={"channel": "sms", "contact": "+251911223344"})
    assert res.status_code == 200
    assert res.json()["status"] == "subscribed"


def test_widget_script_is_served_gzipped(client):
    res = client.get("/widget/assistant.js", headers={"Accept-Encoding": "gzip"})
    assert res.status_code == 200
    assert res.headers.get("content-encoding") == "gzip"


def test_admin_endpoints_require_token_when_configured(container):
    settings = replace(container.settings, admin_token="s3cret")
    secured = TestClient(create_app(build_container(settings, provider=container.provider)))

    assert secured.get("/api/admin/courses").status_code == 401
    assert secured.get("/api/admin/courses", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert secured.get("/api/admin/courses", headers={"X-Admin-Token": "s3cret"}).status_code == 200
    # Learner-facing endpoints stay open.
    assert secured.post("/api/chat", json={"message": "What is AI?"}).status_code == 200
