"""
Automated Tests for Universal Ingestion Pipeline & Admin API Endpoints.
Verifies Markdown parsing, HTML parsing, automatic anchor slug generation,
multi-course scoping isolation, and admin management endpoints.
"""

import pytest
from pathlib import Path
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


def test_bidirectional_multi_course_isolation():
    """
    Test bidirectional multi-course scoping:
    Course A (Python) and Course B (React).
    Verifies that questions in Scope A only match Course A,
    and questions in Scope B only match Course B.
    """
    course_a = {
        "course_id": "course:python-bi-test",
        "course_title": "Python Basics",
        "lesson_url": "/curriculum/python.html",
        "content_type": "markdown",
        "content": "# Python Syntax\nPython uses indentation to define code blocks."
    }
    course_b = {
        "course_id": "course:react-bi-test",
        "course_title": "React Frontend",
        "lesson_url": "/curriculum/react.html",
        "content_type": "markdown",
        "content": "# React Components\nJSX allows writing HTML-like tags inside JavaScript components."
    }

    try:
        # 1. Ingest both
        res_a = client.post("/api/admin/ingest", json=course_a)
        assert res_a.status_code == 200
        res_b = client.post("/api/admin/ingest", json=course_b)
        assert res_b.status_code == 200

        # 2. Query Python question scoped to Python -> answered
        res_q_a = client.post("/api/chat", json={
            "session": "test-learner-1",
            "message": "Why does Python use indentation in code blocks?",
            "scope": "course:python-bi-test"
        })
        assert res_q_a.status_code == 200
        assert res_q_a.json()["status"] == "answered"

        # 3. Query same Python question scoped to React -> not_found
        res_q_a_in_b = client.post("/api/chat", json={
            "session": "test-learner-1",
            "message": "Why does Python use indentation in code blocks?",
            "scope": "course:react-bi-test"
        })
        assert res_q_a_in_b.status_code == 200
        assert res_q_a_in_b.json()["status"] == "not_found"

        # 4. Query React question scoped to React -> answered
        res_q_b = client.post("/api/chat", json={
            "session": "test-learner-2",
            "message": "How does JSX work inside JavaScript components in React?",
            "scope": "course:react-bi-test"
        })
        assert res_q_b.status_code == 200
        assert res_q_b.json()["status"] == "answered"

        # 5. Query same React question scoped to Python -> not_found
        res_q_b_in_a = client.post("/api/chat", json={
            "session": "test-learner-2",
            "message": "How does JSX work inside JavaScript components in React?",
            "scope": "course:python-bi-test"
        })
        assert res_q_b_in_a.status_code == 200
        assert res_q_b_in_a.json()["status"] == "not_found"

    finally:
        # Cleanup
        client.delete("/api/admin/courses/course:python-bi-test")
        client.delete("/api/admin/courses/course:react-bi-test")


def test_admin_ingest_edge_cases():
    """Verify error handling for invalid payloads and missing courses."""
    # Deleting non-existent course returns 404
    res_del = client.delete("/api/admin/courses/course:non-existent-xyz-999")
    assert res_del.status_code == 404
    assert "not found" in res_del.json()["detail"].lower()

    # Ingestion with missing required fields returns 422 (Pydantic validation)
    res_invalid = client.post("/api/admin/ingest", json={"invalid": "payload"})
    assert res_invalid.status_code == 422


def test_widget_scoping_and_citation_anchor_wiring():
    """Verify assistant.js contains dynamic scope detection and in-page anchor resolution."""
    widget_file = Path(__file__).resolve().parent.parent / "widget" / "assistant.js"
    assert widget_file.exists()
    content = widget_file.read_text(encoding="utf-8")

    # Scope detection logic
    assert "detectScope()" in content
    assert "data-scope" in content
    assert "meta[name=\"course-id\"]" in content
    assert "updateScopeBadge()" in content
    assert "alx-scope-badge" in content

    # In-page deep link resolution
    assert "targetEl.scrollIntoView" in content
    assert "targetEl.closest(" in content


