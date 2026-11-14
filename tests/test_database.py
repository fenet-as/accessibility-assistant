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


def test_course_chunks_persistence_in_database(tmp_path):
    from assistant.infrastructure.chunk_store import ChunkStore

    db = Database(tmp_path / "test_courses.db")
    assert db.count_course_chunks() == 0

    sample_chunks = [
        {
            "id": "c1--l1--sec1",
            "scope": "course:c1",
            "course": "Course 1",
            "lesson_id": "l1",
            "title": "Title 1",
            "section": "Sec 1",
            "anchor": "#sec1",
            "url": "/c1/l1#sec1",
            "language": "en",
            "text": "This is sample course text 1 for testing SQLite persistence.",
            "translations": {"am": "ይህ የሙከራ ጽሑፍ 1 ነው"},
            "keywords_en": "sample course",
            "keywords_am": "ሙከራ",
            "synonyms": ["example"],
            "content_hash": "hash1",
            "revision": 1,
        },
        {
            "id": "c1--l2--sec2",
            "scope": "course:c1",
            "course": "Course 1",
            "lesson_id": "l2",
            "title": "Title 2",
            "section": "Sec 2",
            "anchor": "#sec2",
            "url": "/c1/l2#sec2",
            "language": "en",
            "text": "This is sample course text 2 for testing SQLite persistence.",
            "translations": {},
            "keywords_en": "sample lesson 2",
            "keywords_am": "",
            "synonyms": [],
            "content_hash": "hash2",
            "revision": 1,
        },
        {
            "id": "c2--l1--sec1",
            "scope": "course:c2",
            "course": "Course 2",
            "lesson_id": "l1",
            "title": "Title 3",
            "section": "Sec 3",
            "anchor": "#sec3",
            "url": "/c2/l1#sec3",
            "language": "en",
            "text": "This is sample course text 3 for testing isolation.",
            "translations": {},
            "keywords_en": "isolation",
            "keywords_am": "",
            "synonyms": [],
            "content_hash": "hash3",
            "revision": 1,
        },
    ]

    db.save_course_chunks(sample_chunks)
    assert db.count_course_chunks() == 3
    assert db.count_course_chunks(scope="course:c1") == 2
    assert db.count_course_chunks(scope="course:c2") == 1

    c1_chunks = db.list_course_chunks(scope="course:c1")
    assert len(c1_chunks) == 2
    assert c1_chunks[0]["id"] == "c1--l1--sec1"
    assert c1_chunks[0]["translations"]["am"] == "ይህ የሙከራ ጽሑፍ 1 ነው"

    l2_chunks = db.list_course_chunks(scope="course:c1", lesson_id="l2")
    assert len(l2_chunks) == 1
    assert l2_chunks[0]["id"] == "c1--l2--sec2"

    # Verify ChunkStore integration with DB
    store = ChunkStore(tmp_path / "chunks.json", db=db)
    loaded = store.load()
    assert len(loaded) == 3
    assert loaded[0]["id"] == "c1--l1--sec1"

    # Test deletion
    deleted = db.delete_course_chunks(scope="course:c1", lesson_id="l2")
    assert deleted == 1
    assert db.count_course_chunks(scope="course:c1") == 1

    db.delete_course_chunks(scope="%")
    assert db.count_course_chunks() == 0

