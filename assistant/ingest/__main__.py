"""Rebuild the VA-1 course chunks from the Savanna concept page (incremental: only changes are rewritten).

Usage: python -m assistant.ingest
"""

from assistant.config import get_settings
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.ingest.savanna import COURSE_SCOPE, LESSON_ID, parse_concept_file


def main() -> None:
    settings = get_settings()
    source = settings.savanna_dir / "pages" / "concept-with-navigation.html"
    chunks = parse_concept_file(source, settings.faq_translations_path)
    result = ChunkStore(settings.chunks_path).upsert_lesson(COURSE_SCOPE, LESSON_ID, chunks)
    print(
        f"Ingested {COURSE_SCOPE}/{LESSON_ID} into {settings.chunks_path}: "
        f"{result.added} added, {result.updated} updated, {result.unchanged} unchanged, "
        f"{result.removed} removed. Knowledge-base version {result.kb_version}."
    )


if __name__ == "__main__":
    main()
