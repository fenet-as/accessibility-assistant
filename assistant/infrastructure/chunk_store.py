"""File-backed store for course chunks (`chunks.json`).

Writes are atomic (temp file + rename) so a reader never sees a half-written corpus,
and `version` lets every worker process notice when another one changed the file.
"""

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List

Chunk = Dict[str, Any]


class ChunkStore:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.Lock()

    @property
    def version(self) -> int:
        try:
            return self.path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def load(self) -> List[Chunk]:
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, chunks: List[Chunk]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
                os.replace(tmp_name, self.path)
            except BaseException:
                Path(tmp_name).unlink(missing_ok=True)
                raise

    def seed_from(self, source: Path) -> None:
        """First start on a fresh volume: copy the bundled corpus so learners get answers at once."""
        if not self.path.exists() and source.exists() and source.resolve() != self.path.resolve():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            os.close(fd)
            shutil.copyfile(source, tmp_name)
            os.replace(tmp_name, self.path)

    def replace_course(self, scope: str, new_chunks: List[Chunk]) -> None:
        kept = [c for c in self.load() if c.get("scope") != scope]
        self.save(kept + new_chunks)

    def delete_course(self, scope: str) -> bool:
        chunks = self.load()
        kept = [c for c in chunks if c.get("scope") != scope]
        if len(kept) == len(chunks):
            return False
        self.save(kept)
        return True
