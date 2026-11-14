"""Savanna concept page parser."""

from assistant.config import get_settings
from assistant.ingest.savanna import COURSE_SCOPE, parse_concept_file

SOURCE = get_settings().savanna_dir / "pages" / "concept-with-navigation.html"


def test_concept_page_is_split_into_cited_sections():
    chunks = parse_concept_file(SOURCE)
    assert len(chunks) >= 6

    first = chunks[0]
    for key in ("id", "course", "scope", "title", "section", "anchor", "url", "text"):
        assert key in first
    assert first["scope"] == COURSE_SCOPE
    assert len(first["text"]) > 50

    anchors = {c["anchor"] for c in chunks}
    assert "#what-is-shaping-the-future-of-va-work" in anchors
    assert "#artificial-intelligence-and-the-future-of-va-work" in anchors


def test_bundled_chunks_match_the_concept_page(container):
    """assistant/data/chunks.json must be regenerated (python -m assistant.ingest) after page edits."""
    bundled = [c for c in container.courses.store.load() if c.get("scope") == COURSE_SCOPE]
    assert bundled == parse_concept_file(SOURCE)
