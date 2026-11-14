"""Markdown/HTML parsers, the admin ingestion API, and per-course answer isolation."""

from assistant.ingest.parsers import parse_html, parse_markdown, slugify


def ask(client, message, scope):
    return client.post("/api/chat", json={"session": "test-learner", "message": message, "scope": scope}).json()


def test_slugify_converts_titles_to_safe_anchors():
    assert slugify("What is Shaping the Future of VA Work?") == "what-is-shaping-the-future-of-va-work"
    assert slugify("Introduction & Overview") == "introduction-overview"
    assert slugify("AI-Powered Productivity Tools 2026") == "ai-powered-productivity-tools-2026"


def test_markdown_is_split_on_headings():
    chunks = parse_markdown(
        "# Python Basics\nWelcome to Python programming for virtual assistants.\n\n"
        "## Variables and Data Types\nIn Python, variables store data values such as strings, integers, and floats.\n\n"
        "## Functions and Loops\nFunctions are defined using the def keyword to perform reusable tasks.\n",
        course_id="course:python-test",
        course_title="Python Basics",
        lesson_url="/curriculum/python.html",
    )
    assert [c["section"] for c in chunks] == ["Python Basics", "Variables and Data Types", "Functions and Loops"]
    assert chunks[0]["url"] == "/curriculum/python.html#python-basics"
    assert chunks[1]["anchor"] == "#variables-and-data-types"
    assert "variables store data" in chunks[1]["text"]


def test_html_is_split_on_heading_tags_and_keeps_ids():
    chunks = parse_html(
        '<div><h2 id="intro-heading">Lesson Intro</h2><p>This is the introduction to digital workflows.</p>'
        '<h3 id="tools-section">Essential Digital Tools</h3><p>Cloud calendars keep remote work organized.</p></div>',
        course_id="course:tools-test",
        course_title="Digital Tools",
        lesson_url="/pages/tools.html",
    )
    assert [(c["section"], c["anchor"]) for c in chunks] == [
        ("Lesson Intro", "#intro-heading"),
        ("Essential Digital Tools", "#tools-section"),
    ]


def test_ingest_list_query_and_delete(client):
    course = {
        "course_id": "course:python-auto-test",
        "course_title": "Python Programming",
        "lesson_url": "/curriculum/python-syntax.html",
        "content_type": "markdown",
        "content": "# Python Variables and Types\nPython uses dynamic typing for integers, floats, and boolean variables.\n\n"
                   "## Defining Functions\nFunctions are declared using the def keyword and return expressions to callers.\n",
    }
    res = client.post("/api/admin/ingest", json=course)
    assert res.status_code == 200
    assert res.json()["chunks_created"] == 2
    assert "Defining Functions" in res.json()["sections"]

    courses = client.get("/api/admin/courses").json()
    assert any(c["course_id"] == "course:python-auto-test" for c in courses)

    question = "How do you declare a boolean variable in Python?"
    scoped = ask(client, question, "course:python-auto-test")
    assert scoped["status"] == "answered"
    assert scoped["citations"][0]["url"].startswith("/curriculum/python-syntax.html")
    assert ask(client, question, "course:va-1")["status"] == "not_found"

    assert client.delete("/api/admin/courses/course:python-auto-test").json()["status"] == "deleted"
    assert ask(client, question, "course:python-auto-test")["status"] == "not_found"


def test_courses_are_isolated_from_each_other(client):
    python = {"course_id": "course:python-bi-test", "course_title": "Python Basics",
              "content": "# Python Syntax\nPython uses indentation to define code blocks."}
    react = {"course_id": "course:react-bi-test", "course_title": "React Frontend",
             "content": "# React Components\nJSX allows writing HTML-like tags inside JavaScript components."}
    python_q = "Why does Python use indentation in code blocks?"
    react_q = "How does JSX work inside JavaScript components in React?"
    try:
        assert client.post("/api/admin/ingest", json=python).status_code == 200
        assert client.post("/api/admin/ingest", json=react).status_code == 200

        assert ask(client, python_q, "course:python-bi-test")["status"] == "answered"
        assert ask(client, python_q, "course:react-bi-test")["status"] == "not_found"
        assert ask(client, react_q, "course:react-bi-test")["status"] == "answered"
        assert ask(client, react_q, "course:python-bi-test")["status"] == "not_found"
    finally:
        client.delete("/api/admin/courses/course:python-bi-test")
        client.delete("/api/admin/courses/course:react-bi-test")


def test_admin_error_handling(client):
    res = client.delete("/api/admin/courses/course:non-existent-xyz-999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    assert client.post("/api/admin/ingest", json={"invalid": "payload"}).status_code == 422
    empty = {"course_id": "course:empty", "course_title": "Empty", "content": "   "}
    assert client.post("/api/admin/ingest", json=empty).status_code == 400


def test_incremental_lesson_ingest_validation_and_lesson_delete(client):
    lesson = {"course_id": "course:inc-test", "course_title": "Incremental", "lesson_url": "/inc/one.html",
              "content": "## Topic A\nTopic A explains how incremental updates keep unchanged sections.\n\n"
                         "## Topic B\nTopic B explains that changed sections get a new revision number."}
    try:
        first = client.post("/api/admin/ingest", json=lesson).json()
        assert first["lesson_id"] == "one" and first["chunks_created"] == 2
        assert client.get("/api/health").json()["kb_version"] == first["kb_version"]

        lesson["content"] = lesson["content"].replace("new revision number", "higher revision number")
        second = client.post("/api/admin/ingest", json=lesson).json()
        assert (second["chunks_created"], second["chunks_updated"], second["chunks_unchanged"]) == (0, 1, 1)
        assert second["kb_version"] != first["kb_version"]

        bad = {**lesson, "course_id": "not-a-course-id"}
        res = client.post("/api/admin/ingest", json=bad)
        assert res.status_code == 400 and "scope" in res.json()["detail"]

        assert client.delete("/api/admin/courses/course:inc-test/lessons/one").json()["status"] == "deleted"
        assert client.delete("/api/admin/courses/course:inc-test/lessons/one").status_code == 404
    finally:
        client.delete("/api/admin/courses/course:inc-test")


def test_admin_portal_page(client):
    res = client.get("/admin/ingest")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "<title>Course Curriculum Ingestion & Management Portal" in html
    assert 'id="ingest-form"' in html
    assert 'id="courses-table"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert client.get("/api/admin/ui").status_code == 200


def test_widget_scope_detection_and_citation_deep_links(client):
    source = client.get("/widget/assistant.js").text
    for snippet in ("detectScope()", "data-scope", 'meta[name="course-id"]', "updateScopeBadge()",
                    "alx-scope-badge", "targetEl.scrollIntoView", "targetEl.closest("):
        assert snippet in source
