"""SQLite persistence, privacy of stored data, teacher analytics and LTI endpoints."""

import sqlite3

from assistant.infrastructure.database import Database, anonymize


def test_query_logging_feeds_analytics(tmp_path):
    db = Database(tmp_path / "a.db")
    db.log_query("s1", "How do I communicate effectively?", "en", "answered", "Communication")
    db.log_query("s1", "What else about communication?", "en", "answered", "Communication")
    db.log_query("s2", "የስንዴ ዳቦ አዘገጃጀት", "am", "not_found", "unresolved")

    summary = db.analytics_summary()
    assert summary["total_queries"] == 3
    assert summary["languages"] == {"en": 2, "am": 1}
    assert summary["curriculum_gaps"]["unresolved_count"] == 1
    assert summary["top_topics"][0] == {"topic": "Communication", "count": 2}


def test_session_ids_are_never_stored_in_clear(tmp_path):
    db = Database(tmp_path / "a.db")
    db.log_query("sms-+251911223344", "hello", "en", "answered")
    db.log_escalation("HELP-1", "tg-987654", "https://meet.jit.si/x")

    with sqlite3.connect(tmp_path / "a.db") as conn:
        stored = [row[0] for row in conn.execute("SELECT session_id FROM query_logs UNION ALL "
                                                  "SELECT session_id FROM escalations")]
    assert stored == [anonymize("sms-+251911223344"), anonymize("tg-987654")]
    assert not any("251911223344" in s or "987654" in s for s in stored)


def test_chat_is_logged_for_analytics(client):
    before = client.get("/api/analytics/summary").json()["total_queries"]
    client.post("/api/chat", json={"message": "What is shaping the future of VA work?"})
    assert client.get("/api/analytics/summary").json()["total_queries"] == before + 1


def test_analytics_summary_endpoint(client):
    data = client.get("/api/analytics/summary").json()
    for key in ("total_queries", "languages", "top_topics", "curriculum_gaps", "career_gateway"):
        assert key in data


def test_analytics_dashboard_html(client):
    res = client.get("/analytics")
    assert res.status_code == 200
    assert "Teacher & Curriculum Analytics" in res.text
    assert "Curriculum Content Gaps" in res.text


def test_lti_config_manifest(client):
    data = client.get("/api/lti/config.json").json()
    assert data["title"] == "ALX Accessibility Assistant & Tutor"
    for key in ("oidc_initiation_url", "target_link_uri", "public_jwk_url"):
        assert key in data


def test_job_persistence_in_database(tmp_path):
    db = Database(tmp_path / "jobs.db")
    assert db.count_jobs() == 0

    sample_job = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "id": "job-test-1",
        "title": "Software Tester",
        "alternateName": "QA Tester",
        "description": "Test accessible user interfaces.",
        "hiringOrganization": {"@type": "Organization", "name": "EthioTech"},
        "jobLocation": {
            "@type": "Place",
            "address": {"@type": "PostalAddress", "addressLocality": "Addis Ababa", "addressCountry": "ET"},
        },
        "employmentType": "FULL_TIME",
        "qualifications": "Testing basics",
        "accommodationsOffered": ["Screen reader software provided"],
    }
    db.save_job(sample_job)
    assert db.count_jobs() == 1
    retrieved = db.get_job("job-test-1")
    assert retrieved is not None
    assert retrieved["title"] == "Software Tester"
    assert retrieved["hiringOrganization"]["name"] == "EthioTech"

    all_jobs = db.list_jobs()
    assert len(all_jobs) == 1
    assert all_jobs[0]["id"] == "job-test-1"

    assert db.delete_job("job-test-1") is True
    assert db.count_jobs() == 0
    assert db.get_job("job-test-1") is None


def test_lti_launch_endpoint(client):
    data = client.post("/api/lti/launch", json={"user_id": "anon-123"}).json()
    assert data["status"] == "authenticated"
    assert data["standard"] == "LTI-1p3"
