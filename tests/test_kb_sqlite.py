"""Milestone 1: SQLite is the runtime knowledge-base source of truth."""

from dataclasses import replace

from fastapi.testclient import TestClient

from assistant.api.app import create_app
from assistant.container import build_container
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.database import Database
from assistant.ingest.parsers import parse_markdown
from assistant.services.tutor import TutorService
from assistant.infrastructure.providers.faq import OfflineFAQProvider


LESSON_MD = (
    "# Variables\n"
    "A variable is a name that refers to a value stored in memory for later use.\n\n"
    "## Data Types\n"
    "Common data types include integers, floats, strings, and booleans in Python.\n"
)


def _ingest(store: ChunkStore, content: str = LESSON_MD, lesson_id: str = "variables"):
    chunks = parse_markdown(content, "course:py-sqlite", "Python SQLite", f"/py/{lesson_id}.html", lesson_id)
    return store.upsert_lesson("course:py-sqlite", lesson_id, chunks)


def test_ingest_then_answer_from_sqlite(tmp_path):
    db = Database(tmp_path / "kb.db")
    store = ChunkStore(tmp_path / "seed.json", db=db)
    result = _ingest(store)
    assert result.added == 2
    assert db.count_course_chunks() == 2
    assert db.get_kb_version() == result.kb_version

    tutor = TutorService(store, OfflineFAQProvider())
    from assistant.domain.models import ChatRequest

    response = tutor.answer(ChatRequest(message="What are the common data types?", scope="course:py-sqlite"))
    assert response.status.value == "answered"
    assert response.citations
    assert "Data Types" in response.citations[0].section


def test_reingest_keeps_revision_for_unchanged_sections(tmp_path):
    db = Database(tmp_path / "kb.db")
    store = ChunkStore(tmp_path / "seed.json", db=db)
    first = _ingest(store)
    again = _ingest(store)
    assert (again.added, again.updated, again.unchanged) == (0, 0, 2)
    assert again.kb_version == first.kb_version
    revisions = {c["section"]: c["revision"] for c in store.load()}
    assert revisions["Variables"] == 1
    assert revisions["Data Types"] == 1


def test_delete_lesson_removes_answers(tmp_path):
    db = Database(tmp_path / "kb.db")
    store = ChunkStore(tmp_path / "seed.json", db=db)
    _ingest(store, lesson_id="variables")
    _ingest(
        store,
        "# Loops\nA loop repeats a block of code many times until a stop condition is met.\n",
        lesson_id="loops",
    )
    assert store.delete_lesson("course:py-sqlite", "variables") is True
    assert {c["lesson_id"] for c in store.load()} == {"loops"}
    assert db.count_course_chunks() == 1


def test_two_chunk_stores_share_sqlite_writes(tmp_path):
    db_path = tmp_path / "shared.db"
    db_a = Database(db_path)
    db_b = Database(db_path)
    store_a = ChunkStore(tmp_path / "a.json", db=db_a)
    store_b = ChunkStore(tmp_path / "b.json", db=db_b)

    before = store_b.version
    _ingest(store_a)
    assert store_b.version > before
    assert len(store_b.load()) == 2
    assert store_b.kb_version == store_a.kb_version


def test_empty_admin_token_forbidden_unless_open_admin(container):
    closed = replace(container.settings, admin_token="", allow_open_admin=False)
    client = TestClient(create_app(build_container(closed, provider=container.provider)))
    res = client.get("/api/admin/courses")
    assert res.status_code == 403
    assert "ADMIN_TOKEN" in res.json()["detail"]

    opened = replace(container.settings, admin_token="", allow_open_admin=True)
    open_client = TestClient(create_app(build_container(opened, provider=container.provider)))
    assert open_client.get("/api/admin/courses").status_code == 200


def test_cli_ingester_writes_sqlite(tmp_path, monkeypatch):
    from assistant.config import Settings
    from assistant.ingest import __main__ as ingest_main

    db_path = tmp_path / "cli.db"
    chunks_path = tmp_path / "chunks.json"
    settings = Settings(database_path=db_path, chunks_path=chunks_path)
    monkeypatch.setattr(ingest_main, "get_settings", lambda: settings)

    # Seed an empty JSON so seed_store upsert can create the file; CLI also needs savanna page.
    ingest_main.main()

    db = Database(db_path)
    assert db.count_course_chunks() >= 6
    assert db.get_kb_version()
    assert chunks_path.exists()


def test_admin_ingest_persists_only_in_sqlite(client, container):
    payload = {
        "course_id": "course:sqlite-m1",
        "course_title": "SQLite Milestone",
        "lesson_url": "/m1/lesson.html",
        "content_type": "markdown",
        "content": LESSON_MD,
        "keywords_am": "ተለዋዋጭ",
        "synonyms": ["identifier"],
    }
    try:
        res = client.post("/api/admin/ingest", json=payload)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["chunks_created"] == 2
        chunks = [c for c in container.courses.store.load() if c["scope"] == "course:sqlite-m1"]
        assert len(chunks) == 2
        assert "ተለዋዋጭ" in chunks[0]["keywords_am"]
        assert "identifier" in chunks[0]["synonyms"]
        assert container.courses.store.db is not None
        assert container.courses.store.db.count_course_chunks(scope="course:sqlite-m1") == 2
    finally:
        client.delete("/api/admin/courses/course:sqlite-m1")
