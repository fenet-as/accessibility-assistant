"""Downloadable offline course packs for the widget Service Worker / IndexedDB cache."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from assistant.api.dependencies import get_container
from assistant.container import Container
from assistant.services.offline_pack import build_course_pack, list_available_packs, pack_meta

router = APIRouter(prefix="/api/offline", tags=["Offline"])


@router.get("/packs")
def available_packs(container: Container = Depends(get_container)) -> Dict[str, Any]:
    """Courses that can be downloaded for offline study."""
    return {
        "kb_version": container.tutor.kb_version,
        "packs": list_available_packs(container.courses.store),
    }


@router.get("/pack")
def download_pack(
    scope: str = Query(default="course:va-1", description="Course scope to download"),
    container: Container = Depends(get_container),
) -> JSONResponse:
    """Full offline pack: chunks, BM25 index, languages, UI strings and system messages.

    Cacheable by the Service Worker; `kb_version` lets the client invalidate a stale pack.
    """
    try:
        pack = build_course_pack(
            container.courses.store,
            scope,
            kb_version=container.tutor.kb_version,
            low_confidence=container.tutor.low_confidence,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    headers = {
        "Cache-Control": "public, max-age=300",
        "X-ALX-KB-Version": pack["kb_version"],
        "X-ALX-Pack-Format": str(pack["pack_format"]),
        "X-ALX-Pack-Scope": scope,
    }
    return JSONResponse(content=pack, headers=headers)


@router.get("/pack/meta")
def download_pack_meta(
    scope: str = Query(default="course:va-1"),
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    """Lightweight version check used before re-downloading a full pack."""
    try:
        pack = build_course_pack(
            container.courses.store,
            scope,
            kb_version=container.tutor.kb_version,
            low_confidence=container.tutor.low_confidence,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return pack_meta(pack)
