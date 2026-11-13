"""
Automated Tests for Universal Ingestion Pipeline & Admin API Endpoints.
Verifies Markdown parsing, HTML parsing, automatic anchor slug generation,
multi-course scoping isolation, and admin management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from assistant.api.main import app
from assistant.ingest.universal_chunker import UniversalChunker, slugify

client = TestClient(app)


def test_slugify_converts_titles_to_safe_anchors():
    """Verify section titles are cleanly converted to URL-safe HTML anchor slugs."""
    assert slugify("What is Shaping the Future of VA Work?") == "what-is-shaping-the-future-of-va-work"
    assert slugify("Introduction & Overview") == "introduction-overview"
    assert slugify("AI-Powered Productivity Tools 2026") == "ai-powered-productivity-tools-2026"


def test_markdown_chunking():
    """Verify Markdown text is segmented by headings with anchor links."""
    chunker = UniversalChunker()
    md_content = """# Python Basics
Welcome to Python programming for virtual assistants.

## Variables and Data Types
In Python, variables store data values such as strings, integers, and floats.

## Functions and Loops
Functions are defined using the def keyword to perform reusable tasks.
"""
    chunks = chunker.parse_markdown(
        content=md_content,
        course_id="course:python-test",
        course_title="Python Basics",
        lesson_url="/curriculum/python.html"
    )

    assert len(chunks) == 3
    assert chunks[0]["section"] == "Python Basics"
    assert chunks[0]["anchor"] == "#python-basics"
    assert chunks[0]["url"] == "/curriculum/python.html#python-basics"

    assert chunks[1]["section"] == "Variables and Data Types"
    assert chunks[1]["anchor"] == "#variables-and-data-types"
    assert "variables store data" in chunks[1]["text"]

    assert chunks[2]["section"] == "Functions and Loops"
    assert chunks[2]["anchor"] == "#functions-and-loops"


def test_html_chunking():
    """Verify raw HTML is segmented by heading tags."""
    chunker = UniversalChunker()
    html_content = """
    <div>
        <h2 id="intro-heading">Lesson Intro</h2>
        <p>This is the introduction to digital workflows.</p>
        <h3 id="tools-section">Essential Digital Tools</h3>
        <p>Cloud calendars and task managers keep remote work organized.</p>
    </div>
    """
    chunks = chunker.parse_html(
        content=html_content,
        course_id="course:tools-test",
        course_title="Digital Tools",
        lesson_url="/pages/tools.html"
    )

    assert len(chunks) == 2
    assert chunks[0]["section"] == "Lesson Intro"
    assert chunks[0]["anchor"] == "#intro-heading"
    assert chunks[1]["section"] == "Essential Digital Tools"
    assert chunks[1]["anchor"] == "#tools-section"


def test_admin_ingest_and_multi_course_scoping():
    """
    Test end-to-end admin ingestion workflow:
    1. Ingest new Python course via POST /api/admin/ingest.
    2. Verify it appears in GET /api/admin/courses.
    3. Verify scoped querying returns answer when scoped to Python, but NOT when scoped to VA-1.
    4. Clean up via DELETE /api/admin/courses/{course_id}.
    """
    sample_course = {
        "course_id": "course:python-auto-test",
        "course_title": "Python Programming",
        "lesson_url": "/curriculum/python-syntax.html",
        "content_type": "markdown",
        "content": """# Python Variables and Types
Python uses dynamic typing for integers, floats, and boolean variables.

## Defining Functions
Functions are declared using the def keyword and return expressions to callers.
"""
    }

    # 1. Ingest course
    res_ingest = client.post("/api/admin/ingest", json=sample_course)
    assert res_ingest.status_code == 200
    data = res_ingest.json()
    assert data["status"] == "success"
    assert data["chunks_created"] == 2
    assert "Defining Functions" in data["sections"]

    # 2. Verify in course list
    res_list = client.get("/api/admin/courses")
    assert res_list.status_code == 200
    courses = res_list.json()
    assert any(c["course_id"] == "course:python-auto-test" for c in courses)

    # 3. Test multi-course scoping isolation
    # Query Python question with Python scope -> Should succeed
    res_chat_scoped = client.post("/api/chat", json={
        "session": "test-learner",
        "message": "How do you declare a boolean variable in Python?",
        "scope": "course:python-auto-test"
    })
    assert res_chat_scoped.status_code == 200
    chat_data = res_chat_scoped.json()
    assert chat_data["status"] == "answered"
    assert len(chat_data["citations"]) > 0
    assert chat_data["citations"][0]["url"].startswith("/curriculum/python-syntax.html")

    # Query Python question with VA-1 scope -> Must return not_found (isolation guarantee!)
    res_chat_isolated = client.post("/api/chat", json={
        "session": "test-learner",
        "message": "How do you declare a boolean variable in Python?",
        "scope": "course:va-1"
    })
    assert res_chat_isolated.status_code == 200
    isolated_data = res_chat_isolated.json()
    assert isolated_data["status"] == "not_found"

    # 4. Clean up course
    res_del = client.delete("/api/admin/courses/course:python-auto-test")
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert del_data["status"] == "deleted"


def test_admin_ingest_ui_endpoint():
    """Verify that the Admin Ingestion Portal HTML page is accessible and valid."""
    res_ui = client.get("/admin/ingest")
    assert res_ui.status_code == 200
    assert "text/html" in res_ui.headers["content-type"]
    html = res_ui.text
    assert "<title>Course Curriculum Ingestion & Management Portal" in html
    assert 'id="ingest-form"' in html
    assert 'id="courses-table"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html

    # Alias /api/admin/ui
    res_alias = client.get("/api/admin/ui")
    assert res_alias.status_code == 200

