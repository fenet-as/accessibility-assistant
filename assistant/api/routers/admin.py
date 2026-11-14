from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from assistant.api.dependencies import get_container, require_admin
from assistant.api.schemas import IngestRequest, IngestResponse
from assistant.container import Container

router = APIRouter(prefix="/api/admin", tags=["Course Ingestion"], dependencies=[Depends(require_admin)])


@router.post("/ingest", response_model=IngestResponse)
def ingest_course(request: IngestRequest, container: Container = Depends(get_container)) -> IngestResponse:
    """Add or update one lesson (Markdown or HTML); it is answerable immediately on every channel.

    Re-sending a lesson only rewrites the sections that changed; invalid content is rejected with 400.
    """
    try:
        result = container.courses.ingest(
            course_id=request.course_id,
            course_title=request.course_title,
            content=request.content,
            content_type=request.content_type,
            lesson_url=request.lesson_url,
            lesson_id=request.lesson_id,
            lesson_title=request.lesson_title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Course ingestion failed: {exc}")
    return IngestResponse(
        status="success",
        course_id=request.course_id,
        lesson_id=result.chunks[0]["lesson_id"],
        chunks_created=result.added,
        chunks_updated=result.updated,
        chunks_unchanged=result.unchanged,
        chunks_removed=result.removed,
        kb_version=result.kb_version,
        sections=[c["section"] for c in result.chunks],
        sample_url=result.chunks[0]["url"],
    )


@router.get("/courses")
def list_courses(container: Container = Depends(get_container)) -> List[Dict[str, Any]]:
    """Indexed courses with chunk counts and section titles."""
    return container.courses.list_courses()


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, container: Container = Depends(get_container)) -> Dict[str, str]:
    if not container.courses.delete(course_id):
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    return {"status": "deleted", "course_id": course_id}


@router.delete("/courses/{course_id}/lessons/{lesson_id}")
def delete_lesson(course_id: str, lesson_id: str, container: Container = Depends(get_container)) -> Dict[str, str]:
    if not container.courses.delete_lesson(course_id, lesson_id):
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found in '{course_id}'")
    return {"status": "deleted", "course_id": course_id, "lesson_id": lesson_id}
