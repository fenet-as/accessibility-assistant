"""Course management: ingest lesson content into the chunk store, list and delete courses."""

from typing import Any, Dict, List

from assistant.infrastructure.chunk_store import Chunk, ChunkStore
from assistant.ingest.parsers import parse_html, parse_markdown
from assistant.services.tutor import TutorService


class CourseAdminService:
    def __init__(self, store: ChunkStore, tutor: TutorService):
        self.store = store
        self.tutor = tutor

    def ingest(
        self,
        course_id: str,
        course_title: str,
        content: str,
        content_type: str = "markdown",
        lesson_url: str = "/pages/lesson.html",
    ) -> List[Chunk]:
        parse = parse_html if content_type.lower() == "html" else parse_markdown
        chunks = parse(content, course_id, course_title, lesson_url)
        if not chunks:
            raise ValueError("No valid sections or text could be extracted from the content.")
        self.store.replace_course(course_id, chunks)
        self.tutor.reload()
        return chunks

    def delete(self, course_id: str) -> bool:
        deleted = self.store.delete_course(course_id)
        if deleted:
            self.tutor.reload()
        return deleted

    def list_courses(self) -> List[Dict[str, Any]]:
        courses: Dict[str, Dict[str, Any]] = {}
        for chunk in self.store.load():
            course_id = chunk.get("scope") or chunk.get("course", "unknown")
            course = courses.setdefault(course_id, {
                "course_id": course_id,
                "course_title": chunk.get("course") or chunk.get("title", course_id),
                "chunk_count": 0,
                "sections": [],
                "sample_url": chunk.get("url", ""),
            })
            course["chunk_count"] += 1
            section = chunk.get("section")
            if section and section not in course["sections"]:
                course["sections"].append(section)
        return list(courses.values())
