"""Unit tests for Course Content Ingestion and Semantic Chunker."""
from pathlib import Path
from assistant.ingest.chunker import CourseChunker, run_ingestion


def test_chunker_extracts_sections():
    base_dir = Path(__file__).resolve().parent.parent.parent
    source = base_dir / "savanna-static" / "pages" / "concept-with-navigation.html"
    dest = base_dir / "assistant" / "data" / "chunks.json"

    assert source.exists(), f"Source file does not exist: {source}"

    chunks = run_ingestion(source, dest)
    assert len(chunks) >= 6, "Expected at least 6 semantic chunks extracted"

    # Check structure of the first chunk
    first_chunk = chunks[0]
    assert "id" in first_chunk
    assert "course" in first_chunk
    assert "title" in first_chunk
    assert "section" in first_chunk
    assert "anchor" in first_chunk
    assert "url" in first_chunk
    assert "text" in first_chunk
    assert len(first_chunk["text"]) > 50

    # Verify that anchors exist
    anchors = [c["anchor"] for c in chunks if c["anchor"]]
    assert "#what-is-shaping-the-future-of-va-work" in anchors
    assert "#artificial-intelligence-and-the-future-of-va-work" in anchors

