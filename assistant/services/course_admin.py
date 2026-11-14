"""Course management: ingest lessons incrementally into the chunk store, list and delete content."""

from typing import Any, Dict, List, Optional

from assistant.infrastructure.chunk_store import ChunkStore, UpsertResult
from assistant.ingest.parsers import lesson_id_from_url, parse_html, parse_markdown
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
        lesson_id: Optional[str] = None,
        lesson_title: Optional[str] = None,
    ) -> UpsertResult:
        """Add or update one lesson; other lessons of the course and other courses are untouched.

        Raises ValueError (listing every problem) if the content is empty or invalid; nothing is indexed then.
        """
        lesson_id = lesson_id or lesson_id_from_url(lesson_url)
        parse = parse_html if content_type.lower() == "html" else parse_markdown
        chunks = parse(content, course_id, course_title, lesson_url, lesson_id, lesson_title)
        if not chunks:
            raise ValueError("No valid sections or text could be extracted from the content.")
        result = self.store.upsert_lesson(course_id, lesson_id, chunks)
        self.tutor.reload()
        return result

    def delete(self, course_id: str) -> bool:
        deleted = self.store.delete_course(course_id)
        if deleted:
            self.tutor.reload()
        return deleted

    def delete_lesson(self, course_id: str, lesson_id: str) -> bool:
        deleted = self.store.delete_lesson(course_id, lesson_id)
        if deleted:
            self.tutor.reload()
        return deleted

    def list_courses(self) -> List[Dict[str, Any]]:
        courses: Dict[str, Dict[str, Any]] = {}
        for chunk in self.store.load():
            course = courses.setdefault(chunk["scope"], {
                "course_id": chunk["scope"],
                "course_title": chunk["course"],
                "chunk_count": 0,
                "lessons": [],
                "sections": [],
                "sample_url": chunk["url"],
            })
            course["chunk_count"] += 1
            if chunk["lesson_id"] not in course["lessons"]:
                course["lessons"].append(chunk["lesson_id"])
            if chunk["section"] not in course["sections"]:
                course["sections"].append(chunk["section"])
        return list(courses.values())
