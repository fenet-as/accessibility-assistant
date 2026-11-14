"""Rebuild the VA-1 course chunks from the Savanna concept page.

Usage: python -m assistant.ingest
"""

from assistant.config import get_settings
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.ingest.savanna import COURSE_SCOPE, parse_concept_file


def main() -> None:
    settings = get_settings()
    source = settings.savanna_dir / "pages" / "concept-with-navigation.html"
    chunks = parse_concept_file(source)
    ChunkStore(settings.chunks_path).replace_course(COURSE_SCOPE, chunks)
    print(f"Ingestion complete: {len(chunks)} chunks for {COURSE_SCOPE} written to {settings.chunks_path}")


if __name__ == "__main__":
    main()
