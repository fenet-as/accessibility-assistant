"""Rebuild VA-1 course chunks from the lesson manifest.

Official Savanna concept HTML is ingested as source_kind=course.
Markdown study notes are ingested as source_kind=supplemental and ranked lower
when an official section also matches.

Writes into SQLite (runtime source of truth) and keeps chunks.json seed in sync.

Usage: python -m assistant.ingest
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from assistant.config import DATA_DIR, PROJECT_ROOT, get_settings
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.database import Database
from assistant.ingest.parsers import parse_markdown
from assistant.ingest.savanna import COURSE_NAME, COURSE_SCOPE, LESSON_ID, parse_concept_file

MANIFEST_PATH = DATA_DIR / "lessons" / "manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _mark_source(chunks: List[Dict[str, Any]], source_kind: str) -> List[Dict[str, Any]]:
    for chunk in chunks:
        chunk["source_kind"] = source_kind
    return chunks


# Section title → learner phrases that should rank this section (not the whole lesson).
_SECTION_SYNONYMS = {
    "Freelancing and Employment Paths": [
        "ፍሪላንሲንግ",
        "what is freelancing",
        "remote employment",
        "freelancing vs employment",
    ],
    "Where Do Virtual Assistants Work?": [
        "where do virtual assistants work",
        "where do vas work",
    ],
    "Getting Started as a Virtual Assistant": [
        "how can I become a virtual assistant",
        "become a va",
        "how do I become a va",
    ],
    "Skills Clients Value": [
        "skills a virtual assistant needs",
        "what skills does a va need",
    ],
    "Common Virtual Assistant Responsibilities": [
        "virtual assistant responsibilities",
        "what does a va do",
    ],
}


def _apply_lesson_metadata(chunks: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    for chunk in chunks:
        synonyms = list(chunk.get("synonyms") or [])
        for syn in spec.get("synonyms") or []:
            if syn and syn not in synonyms:
                synonyms.append(syn)
        for syn in _SECTION_SYNONYMS.get(chunk.get("section") or "", []):
            if syn and syn not in synonyms:
                synonyms.append(syn)
        chunk["synonyms"] = synonyms
        am = (spec.get("keywords_am") or "").strip()
        if am:
            prev = (chunk.get("keywords_am") or "").strip()
            chunk["keywords_am"] = f"{prev} {am}".strip()
        chunk["source_kind"] = spec.get("source_kind") or "supplemental"
    return chunks


def _load_official(store: ChunkStore, manifest: Dict[str, Any], faq_path: Path) -> Any:
    totals = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0, "kb_version": ""}
    for spec in manifest.get("official_lessons") or []:
        if spec.get("kind") != "savanna_concept":
            print(f"Skipping unsupported official lesson kind: {spec.get('kind')}")
            continue
        path = _resolve(spec["path"])
        if not path.exists():
            print(f"Skipping missing official lesson: {path}")
            continue
        chunks = _mark_source(parse_concept_file(path, faq_path), spec.get("source_kind") or "course")
        lesson_id = spec.get("lesson_id") or LESSON_ID
        result = store.upsert_lesson(manifest.get("course_id") or COURSE_SCOPE, lesson_id, chunks)
        for key in ("added", "updated", "unchanged", "removed"):
            totals[key] += getattr(result, key)
        totals["kb_version"] = result.kb_version
    return totals


def _load_supplemental(store: ChunkStore, manifest: Dict[str, Any]) -> List[Any]:
    course_id = manifest.get("course_id") or COURSE_SCOPE
    course_title = manifest.get("course_title") or COURSE_NAME
    results = []
    for spec in manifest.get("supplemental_lessons") or []:
        path = _resolve(spec["path"])
        if not path.exists():
            print(f"Skipping missing supplemental lesson: {path}")
            continue
        chunks = parse_markdown(
            path.read_text(encoding="utf-8"),
            course_id,
            course_title,
            lesson_url=spec.get("lesson_url") or f"/pages/{spec['lesson_id']}.html",
            lesson_id=spec["lesson_id"],
            lesson_title=spec.get("lesson_title") or spec["lesson_id"],
        )
        chunks = _apply_lesson_metadata(chunks, spec)
        results.append(store.upsert_lesson(course_id, spec["lesson_id"], chunks))
    return results


def main() -> None:
    settings = get_settings()
    manifest = load_manifest()
    db = Database(settings.database_path)
    store = ChunkStore(settings.chunks_path, db=db)

    totals = _load_official(store, manifest, settings.faq_translations_path)
    for lesson in _load_supplemental(store, manifest):
        for key in ("added", "updated", "unchanged", "removed"):
            totals[key] += getattr(lesson, key)
        totals["kb_version"] = lesson.kb_version

    # Keep the seed file aligned so new environments get the same corpus on first boot.
    seed_store = ChunkStore(settings.chunks_path)
    _load_official(seed_store, manifest, settings.faq_translations_path)
    _load_supplemental(seed_store, manifest)

    chunk_count = len(store.load())
    supplemental = sum(1 for c in store.load() if c.get("source_kind") == "supplemental")
    print(
        f"Ingested {manifest.get('course_id') or COURSE_SCOPE} into SQLite ({settings.database_path}) "
        f"and seed file {settings.chunks_path}: "
        f"{totals['added']} added, {totals['updated']} updated, {totals['unchanged']} unchanged, "
        f"{totals['removed']} removed. Knowledge-base version {totals['kb_version']}. "
        f"Total chunks indexed: {chunk_count} ({supplemental} supplemental)."
    )


if __name__ == "__main__":
    main()
