"""Chunk schema validation, de-duplication, anchors, incremental updates and KB versioning."""

import json

import pytest

from assistant.domain.knowledge import validate_chunks
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.ingest.parsers import parse_markdown

LESSON = """Intro paragraph about the course and what learners will practise here.

## Variables
A variable is a name that refers to a value stored in memory.

## Variables
A second section with the same heading but different explanatory content.

## Copy
A variable is a name that refers to a value stored in memory.
"""


def ingest(store, content, lesson_id="basics"):
    chunks = parse_markdown(content, "course:py", "Python", f"/py/{lesson_id}.html", lesson_id)
    return store.upsert_lesson("course:py", lesson_id, chunks)


def test_invalid_content_is_rejected_with_every_problem_listed():
    bad = [
        {"id": "x", "scope": "py", "course": "Py", "title": "T", "section": "S", "url": "/a", "text": "short"},
        {"id": "y", "scope": "course:py", "course": "Py", "title": "T", "section": "", "url": "a",
         "text": "long enough text for one section here", "language": "fr"},
    ]
    with pytest.raises(ValueError) as error:
        validate_chunks(bad)
    message = str(error.value)
    for problem in ("scope", "text", "section", "url", "language"):
        assert problem in message


def test_duplicate_sections_are_dropped_and_anchors_stay_unique():
    chunks = parse_markdown(LESSON, "course:py", "Python", "/py/basics.html")
    assert [c["section"] for c in chunks] == ["Introduction & Overview", "Variables", "Variables"]
    anchors = [c["anchor"] for c in chunks]
    assert anchors == ["#introduction-overview", "#variables", "#variables-2"]
    assert len({c["id"] for c in chunks}) == 3
    assert chunks[2]["url"].endswith("#variables-2")


def test_incremental_update_only_touches_changed_sections(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    first = ingest(store, LESSON)
    assert (first.added, first.updated, first.unchanged, first.removed) == (3, 0, 0, 0)

    again = ingest(store, LESSON)
    assert (again.added, again.updated, again.unchanged) == (0, 0, 3)
    assert again.kb_version == first.kb_version

    edited = ingest(store, LESSON.replace("stored in memory", "kept in memory"))
    assert (edited.updated, edited.unchanged) == (1, 2)
    assert edited.kb_version != first.kb_version
    revisions = {c["anchor"]: c["revision"] for c in store.load()}
    assert revisions["#variables"] == 2 and revisions["#introduction-overview"] == 1


def test_other_lessons_and_courses_are_untouched(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    ingest(store, LESSON, "basics")
    ingest(store, "## Loops\nA loop repeats a block of code many times.", "loops")
    ingest(store, "## Variables\nRewritten lesson body with entirely new wording.", "basics")
    lessons = {c["lesson_id"] for c in store.load()}
    assert lessons == {"basics", "loops"}
    assert store.delete_lesson("course:py", "loops")
    assert {c["lesson_id"] for c in store.load()} == {"basics"}


def test_file_records_schema_and_kb_version_and_legacy_lists_still_load(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    result = ingest(store, LESSON)
    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert document["schema_version"] == 2 and document["kb_version"] == result.kb_version

    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps([{
        "id": "va-intro-1", "course": "VA-1", "scope": "course:va-1", "title": "Future of VA",
        "section": "Intro", "anchor": "#intro", "url": "/p.html#intro", "text": "A legacy chunk without new fields.",
    }]), encoding="utf-8")
    [chunk] = ChunkStore(legacy).load()
    assert chunk["lesson_id"] == "future-of-va" and chunk["content_hash"] and chunk["revision"] == 1
