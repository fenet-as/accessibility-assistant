"""Knowledge base store: SQLite is the runtime source of truth; `chunks.json` is seed-only.

When a Database is wired in, lesson upserts and deletes touch only the affected rows
inside one transaction and bump shared `kb_meta.revision` so every worker reloads.
File-only mode (tests without a database) still writes the JSON document atomically.
"""

import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from assistant.domain.knowledge import SCHEMA_VERSION, compute_kb_version, validate_chunks

Chunk = Dict[str, Any]
LEGACY_ID_MARKER = "--"


def _page(url: str) -> str:
    return url.split("#")[0]


@dataclass
class UpsertResult:
    added: int
    updated: int
    unchanged: int
    removed: int
    kb_version: str
    chunks: List[Chunk]


class ChunkStore:
    def __init__(self, path: Path, db: Optional[Any] = None):
        self.path = Path(path)
        self.db = db
        self._write_lock = threading.Lock()

    @property
    def version(self) -> int:
        """Opaque change counter: SQLite kb_meta.revision, or file mtime in file-only mode."""
        if self.db is not None:
            return self.db.get_kb_revision()
        try:
            return self.path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def load(self) -> List[Chunk]:
        """Validated chunks from SQLite when configured, otherwise from the JSON seed file."""
        if self.db is not None:
            raw = self.db.list_course_chunks()
            return validate_chunks(raw) if raw else []
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data["chunks"] if isinstance(data, dict) else data
        return validate_chunks(raw)

    def save(self, chunks: List[Chunk]) -> str:
        """Replace the whole corpus. Prefer upsert_lesson for incremental admin ingest."""
        chunks = validate_chunks(chunks)
        kb_version = compute_kb_version(chunks)
        if self.db is not None:
            with self._write_lock:
                return self.db.replace_all_course_chunks(chunks)
        return self._save_file(chunks, kb_version)

    def _save_file(self, chunks: List[Chunk], kb_version: Optional[str] = None) -> str:
        chunks = validate_chunks(chunks)
        kb_version = kb_version or compute_kb_version(chunks)
        document = {"schema_version": SCHEMA_VERSION, "kb_version": kb_version, "chunks": chunks}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(document, f, ensure_ascii=False, indent=2)
                os.replace(tmp_name, self.path)
            except BaseException:
                Path(tmp_name).unlink(missing_ok=True)
                raise
        return kb_version

    def seed_from(self, source: Path) -> None:
        """First start on a fresh volume: seed SQLite (and optionally the local JSON path)."""
        if self.db is not None and self.db.count_course_chunks() == 0 and source.exists():
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data["chunks"] if isinstance(data, dict) else data
            chunks = validate_chunks(raw)
            with self._write_lock:
                self.db.replace_all_course_chunks(chunks)

        if not self.path.exists() and source.exists() and source.resolve() != self.path.resolve():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            os.close(fd)
            shutil.copyfile(source, tmp_name)
            os.replace(tmp_name, self.path)

    def upsert_lesson(self, scope: str, lesson_id: str, new_chunks: List[Chunk]) -> UpsertResult:
        """Replace one lesson of one course; other lessons and courses are untouched.

        Unchanged sections keep their revision; changed ones get revision + 1.
        """
        new_chunks = validate_chunks(new_chunks)
        pages = {_page(c["url"]) for c in new_chunks}

        def same_lesson(chunk: Chunk) -> bool:
            # Chunks written before lesson ids existed (legacy ids without "--") are matched by their page.
            legacy_match = LEGACY_ID_MARKER not in chunk["id"] and _page(chunk["url"]) in pages
            return chunk["scope"] == scope and (chunk["lesson_id"] == lesson_id or legacy_match)

        existing = self.load()
        previous = {c["id"]: c for c in existing if same_lesson(c)}
        kept = [c for c in existing if not same_lesson(c)]

        added = updated = unchanged = 0
        for chunk in new_chunks:
            old = previous.get(chunk["id"])
            if old is None:
                added += 1
            elif old["content_hash"] == chunk["content_hash"]:
                chunk["revision"] = old["revision"]
                unchanged += 1
            else:
                chunk["revision"] = old["revision"] + 1
                updated += 1
        removed = len(set(previous) - {c["id"] for c in new_chunks})

        if self.db is not None:
            with self._write_lock:
                kb_version = self.db.replace_lesson_chunks(set(previous.keys()), new_chunks)
        else:
            kb_version = self._save_file(kept + new_chunks)
        return UpsertResult(added, updated, unchanged, removed, kb_version, new_chunks)

    @property
    def kb_version(self) -> str:
        if self.db is not None:
            stored = self.db.get_kb_version()
            if stored:
                return stored
        return compute_kb_version(self.load())

    def delete_course(self, scope: str) -> bool:
        return self._delete(lambda c: c["scope"] == scope)

    def delete_lesson(self, scope: str, lesson_id: str) -> bool:
        return self._delete(lambda c: c["scope"] == scope and c["lesson_id"] == lesson_id)

    def _delete(self, matches) -> bool:
        chunks = self.load()
        remove_ids = {c["id"] for c in chunks if matches(c)}
        if not remove_ids:
            return False
        if self.db is not None:
            with self._write_lock:
                self.db.replace_lesson_chunks(remove_ids, [])
        else:
            self._save_file([c for c in chunks if c["id"] not in remove_ids])
        return True
