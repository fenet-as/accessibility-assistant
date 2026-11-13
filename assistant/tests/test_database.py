"""Tests for SQLite Database, Teacher Analytics, and LTI 1.3 Endpoints."""

import pytest
from fastapi.testclient import TestClient
from assistant.api.main import app
from assistant.core.database import (
    log_query,
    add_subscription,
    add_accommodation,
    get_analytics_summary
)

client = TestClient(app)


def test_sqlite_query_logging():
    """Verify queries are logged into SQLite and retrieved in analytics."""
    log_query("test-sess-01", "How do I communicate effectively?", "en", "answered", "Communication", "normal")
    log_query("test-sess-02", "የስንዴ ዳቦ አዘገጃጀት", "am", "not_found", "unresolved", "normal")

    summary = get_analytics_summary()
    assert summary["total_queries"] >= 2
    assert "en" in summary["languages"]
    assert "am" in summary["languages"]
    assert summary["curriculum_gaps"]["unresolved_count"] >= 1


def test_analytics_summary_endpoint():
    """Verify /api/analytics/summary returns k-anonymity summary."""
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_queries" in data
    assert "languages" in data
    assert "curriculum_gaps" in data
    assert "career_gateway" in data


def test_analytics_dashboard_html():
    """Verify /analytics web page renders with teacher metrics."""
    res = client.get("/analytics")
    assert res.status_code == 200
    assert "Teacher & Curriculum Analytics" in res.text
    assert "Curriculum Content Gaps" in res.text


def test_lti_config_manifest():
    """Verify Level 3 LTI 1.3 configuration endpoint."""
    res = client.get("/api/lti/config.json")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "ALX Accessibility Assistant & Tutor"
    assert "oidc_initiation_url" in data
    assert "target_link_uri" in data
    assert "public_jwk_url" in data


def test_lti_launch_endpoint():
    """Verify LTI 1.3 launch handler."""
    res = client.post("/api/lti/launch", json={"user_id": "anon-123"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "authenticated"
    assert data["standard"] == "LTI-1p3"

