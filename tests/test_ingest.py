"""Savanna concept page parser."""

from assistant.config import get_settings
from assistant.domain.knowledge import validate_chunks
from assistant.ingest.savanna import COURSE_SCOPE, LESSON_ID, parse_concept_file

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
    bundled = [c for c in container.courses.store.load() if c["scope"] == COURSE_SCOPE]
    parsed = validate_chunks(parse_concept_file(SOURCE, get_settings().faq_translations_path))
    strip = lambda chunks: [{k: v for k, v in c.items() if k != "revision"} for c in chunks]
    assert strip(bundled) == strip(parsed)


def test_concept_page_chunks_carry_lesson_translations_and_stable_ids():
    chunks = parse_concept_file(SOURCE, get_settings().faq_translations_path)
    assert {c["lesson_id"] for c in chunks} == {LESSON_ID}
    assert all(c["id"] == f"va-1--{LESSON_ID}--{c['anchor'].lstrip('#')}" for c in chunks)
    ai = next(c for c in chunks if "artificial-intelligence" in c["anchor"])
    assert "am" in ai["translations"] and ai["synonyms"]
