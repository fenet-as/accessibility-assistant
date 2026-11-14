"""Build a downloadable offline course pack: chunks, search index, UI and system messages.

The inverted index is serialized from the same BM25Index the online tutor uses, so offline
ranking reuses the server's indexing work. Offline answering is extractive only — never
cloud AI generation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from assistant import __version__
from assistant.domain.language import UI_STRINGS, language_catalog
from assistant.domain.messages import NEEDS_CLARIFICATION, NOT_FOUND, TRANSLATION_UNAVAILABLE
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.retrieval import (
    CONFIDENCE_COVERAGE,
    CONFIDENCE_PHRASE,
    CONFIDENCE_TITLE,
    SYNONYM_WEIGHT,
    WEIGHT_BM25,
    WEIGHT_COVERAGE,
    WEIGHT_KEYWORD,
    WEIGHT_PHRASE,
    WEIGHT_TITLE,
    BM25Index,
)
from assistant.infrastructure.text_analysis import ACRONYMS, STOP_WORDS, SYNONYMS
from assistant.services.tutor import HIGH_CONFIDENCE, TOP_K, WIDE_K

PACK_FORMAT_VERSION = 1


def _tokenizer_payload() -> Dict[str, Any]:
    return {
        "stop_words": sorted(STOP_WORDS),
        "acronyms": [[acronym, list(words)] for acronym, words in ACRONYMS],
        "synonyms": {term: sorted(others) for term, others in SYNONYMS.items()},
    }


def build_course_pack(
    store: ChunkStore,
    scope: str,
    *,
    kb_version: str = "",
    low_confidence: float = 0.35,
) -> Dict[str, Any]:
    """Assemble one course's offline pack. Raises LookupError if the scope has no chunks."""
    chunks = [c for c in store.load() if c.get("scope") == scope]
    if not chunks:
        raise LookupError(f"No indexed content for scope '{scope}'")

    index = BM25Index(chunks)
    return {
        "pack_format": PACK_FORMAT_VERSION,
        "app_version": __version__,
        "kb_version": kb_version or store.kb_version,
        "scope": scope,
        "course_title": chunks[0]["course"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "thresholds": {
            "high_confidence": HIGH_CONFIDENCE,
            "low_confidence": low_confidence,
            "top_k": TOP_K,
            "wide_k": WIDE_K,
        },
        "ranking": {
            "synonym_weight": SYNONYM_WEIGHT,
            "weights": {
                "bm25": WEIGHT_BM25,
                "coverage": WEIGHT_COVERAGE,
                "title": WEIGHT_TITLE,
                "keyword": WEIGHT_KEYWORD,
                "phrase": WEIGHT_PHRASE,
            },
            "confidence": {
                "coverage": CONFIDENCE_COVERAGE,
                "title": CONFIDENCE_TITLE,
                "phrase": CONFIDENCE_PHRASE,
            },
        },
        "tokenizer": _tokenizer_payload(),
        "languages": language_catalog(),
        "ui": UI_STRINGS,
        "messages": {
            "not_found": NOT_FOUND,
            "needs_clarification": NEEDS_CLARIFICATION,
            "translation_unavailable": TRANSLATION_UNAVAILABLE,
        },
        "index": index.serialize(),
        "offline_capabilities": {
            "local_retrieval": True,
            "extractive_answers": True,
            "cloud_ai": False,
            "note": "Offline mode searches downloaded course content only. It does not run cloud AI.",
        },
    }


def list_available_packs(store: ChunkStore) -> List[Dict[str, Any]]:
    courses: Dict[str, Dict[str, Any]] = {}
    for chunk in store.load():
        scope = chunk["scope"]
        course = courses.setdefault(scope, {
            "scope": scope,
            "course_title": chunk["course"],
            "chunk_count": 0,
            "lessons": set(),
            "languages": set(chunk.get("translations", {})),
        })
        course["chunk_count"] += 1
        course["lessons"].add(chunk.get("lesson_id", ""))
        course["languages"].update(chunk.get("translations", {}).keys())
        course["languages"].add("en")
    return [{
        "scope": c["scope"],
        "course_title": c["course_title"],
        "chunk_count": c["chunk_count"],
        "lesson_count": len([x for x in c["lessons"] if x]),
        "languages": sorted(c["languages"]),
        "pack_url": f"/api/offline/pack?scope={c['scope']}",
    } for c in courses.values()]


def pack_meta(pack: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pack_format": pack["pack_format"],
        "app_version": pack["app_version"],
        "kb_version": pack["kb_version"],
        "scope": pack["scope"],
        "course_title": pack["course_title"],
        "generated_at": pack["generated_at"],
        "chunk_count": pack["chunk_count"],
    }
