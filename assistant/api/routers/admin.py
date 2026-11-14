from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from assistant.api.dependencies import get_container, require_admin
from assistant.api.schemas import IngestRequest, IngestResponse
from assistant.container import Container

router = APIRouter(prefix="/api/admin", tags=["Course Ingestion"], dependencies=[Depends(require_admin)])


@router.post("/ingest", response_model=IngestResponse)
def ingest_course(request: IngestRequest, container: Container = Depends(get_container)) -> IngestResponse:
    """Index Markdown or HTML lesson content; it is answerable immediately on every channel."""
    try:
        chunks = container.courses.ingest(
            course_id=request.course_id,
            course_title=request.course_title,
            content=request.content,
            content_type=request.content_type,
            lesson_url=request.lesson_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Course ingestion failed: {exc}")
    return IngestResponse(
        status="success",
        course_id=request.course_id,
        chunks_created=len(chunks),
        sections=[c["section"] for c in chunks],
        sample_url=chunks[0]["url"],
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
