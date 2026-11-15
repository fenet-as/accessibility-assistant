"""Course management: ingest lessons incrementally into the chunk store, list and delete content."""

import logging
import re
from typing import Any, Dict, List, Optional

from assistant.infrastructure.chunk_store import ChunkStore, UpsertResult
from assistant.ingest.parsers import lesson_id_from_url, parse_html, parse_markdown
from assistant.services.tutor import TutorService

logger = logging.getLogger(__name__)

_MARKDOWN_HEADING = re.compile(r"^#{1,4}\s+\S", re.MULTILINE)
_HTML_HEADING = re.compile(r"<h[1-6]\b", re.IGNORECASE)
MIN_SECTION_CHARS = 20


class CourseAdminService:
    def __init__(self, store: ChunkStore, tutor: TutorService, max_content_chars: int = 500_000):
        self.store = store
        self.tutor = tutor
        self.max_content_chars = max_content_chars

    def ingest(
        self,
        course_id: str,
        course_title: str,
        content: str,
        content_type: str = "markdown",
        lesson_url: str = "/pages/lesson.html",
        lesson_id: Optional[str] = None,
        lesson_title: Optional[str] = None,
        translations: Optional[Dict[str, str]] = None,
        keywords_am: Optional[str] = None,
        synonyms: Optional[List[str]] = None,
    ) -> UpsertResult:
        """Add or update one lesson; other lessons of the course and other courses are untouched.

        Raises ValueError (listing every problem) if the content is empty or invalid; nothing is indexed then.
        """
        self._validate_content(content, content_type)
        lesson_id = lesson_id or lesson_id_from_url(lesson_url)
        parse = parse_html if content_type.lower() == "html" else parse_markdown
        chunks = parse(content, course_id, course_title, lesson_url, lesson_id, lesson_title)
        if not chunks:
            raise ValueError("No valid sections or text could be extracted from the content.")
        short = [c["section"] for c in chunks if len(c.get("text", "")) < MIN_SECTION_CHARS]
        if short:
            raise ValueError(
                f"Sections below {MIN_SECTION_CHARS} characters: {', '.join(short)}. "
                "Add more lesson text under each heading."
            )
        if translations or keywords_am or synonyms:
            for chunk in chunks:
                if translations:
                    merged = dict(chunk.get("translations") or {})
                    merged.update({k: v for k, v in translations.items() if v})
                    chunk["translations"] = merged
                if keywords_am:
                    existing = (chunk.get("keywords_am") or "").strip()
                    chunk["keywords_am"] = f"{existing} {keywords_am}".strip()
                if synonyms:
                    existing_syn = list(chunk.get("synonyms") or [])
                    for syn in synonyms:
                        if syn and syn not in existing_syn:
                            existing_syn.append(syn)
                    chunk["synonyms"] = existing_syn
        result = self.store.upsert_lesson(course_id, lesson_id, chunks)
        self.tutor.reload()
        logger.info(
            "ingest course=%s lesson=%s added=%s updated=%s unchanged=%s removed=%s kb_version=%s",
            course_id,
            lesson_id,
            result.added,
            result.updated,
            result.unchanged,
            result.removed,
            result.kb_version,
        )
        return result

    def _validate_content(self, content: str, content_type: str) -> None:
        if not content or not content.strip():
            raise ValueError("Content is empty.")
        if len(content) > self.max_content_chars:
            raise ValueError(
                f"Content exceeds the {self.max_content_chars} character limit "
                f"({len(content)} characters received)."
            )
        kind = content_type.lower()
        if kind == "markdown" and not _MARKDOWN_HEADING.search(content):
            raise ValueError("Markdown lessons need at least one heading (# … ####).")
        if kind == "html" and not _HTML_HEADING.search(content):
            # Plain HTML without headings is allowed only if there is substantial body text;
            # parsers create a single Introduction section in that case.
            if len(content.strip()) < MIN_SECTION_CHARS * 2:
                raise ValueError("HTML lessons need heading tags (h1–h6) or substantial body text.")

    def delete(self, course_id: str) -> bool:
        deleted = self.store.delete_course(course_id)
        if deleted:
            self.tutor.reload()
            logger.info("deleted course=%s kb_version=%s", course_id, self.store.kb_version)
        return deleted

    def delete_lesson(self, course_id: str, lesson_id: str) -> bool:
        deleted = self.store.delete_lesson(course_id, lesson_id)
        if deleted:
            self.tutor.reload()
            logger.info(
                "deleted course=%s lesson=%s kb_version=%s",
                course_id,
                lesson_id,
                self.store.kb_version,
            )
        return deleted

    def list_courses(self) -> List[Dict[str, Any]]:
        courses: Dict[str, Dict[str, Any]] = {}
        kb_version = self.store.kb_version
        for chunk in self.store.load():
            course = courses.setdefault(chunk["scope"], {
                "course_id": chunk["scope"],
                "course_title": chunk["course"],
                "chunk_count": 0,
                "lessons": [],
                "sections": [],
                "sample_url": chunk["url"],
                "kb_version": kb_version,
            })
            course["chunk_count"] += 1
            if chunk["lesson_id"] not in course["lessons"]:
                course["lessons"].append(chunk["lesson_id"])
            if chunk["section"] not in course["sections"]:
                course["sections"].append(chunk["section"])
        return list(courses.values())
