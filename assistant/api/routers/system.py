"""Health, analytics data and the server-rendered HTML tools (dashboards, simulator, audit)."""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse

from assistant import __version__
from assistant.api.dependencies import get_container
from assistant.container import Container
from assistant.domain.language import AUTO, SUPPORTED_LANGUAGES, UI_STRINGS, language_catalog

PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"
HOME_PAGE = "/savanna/pages/concept-with-navigation.html"

router = APIRouter()


def _page(name: str) -> FileResponse:
    return FileResponse(PAGES_DIR / name, media_type="text/html")


@router.get("/api/health", tags=["System"])
def health(container: Container = Depends(get_container)) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "provider": container.provider.name,
        "indexed_chunks": container.tutor.indexed_chunks,
        "kb_version": container.tutor.kb_version,
        "languages": list(SUPPORTED_LANGUAGES),
        "version": __version__,
    }


@router.get("/api/languages", tags=["System"])
def languages() -> Dict[str, Any]:
    """Centralized language configuration for the widget (names, scripts, RTL, speech tags, UI copy)."""
    return {
        "default": AUTO,
        "supported": list(SUPPORTED_LANGUAGES),
        "languages": language_catalog(),
        "ui_auto": UI_STRINGS["en"],
    }


@router.get("/api/analytics/summary", tags=["Analytics"])
def analytics_summary(container: Container = Depends(get_container)) -> Dict[str, Any]:
    """Aggregate, anonymous statistics for teachers. No names, phones or IDs."""
    return container.analytics.summary()


@router.get("/analytics", include_in_schema=False)
def analytics_page() -> FileResponse:
    return _page("analytics.html")


@router.get("/admin/ingest", include_in_schema=False)
@router.get("/api/admin/ui", include_in_schema=False)
def admin_ingest_page() -> FileResponse:
    return _page("admin_ingest.html")


@router.get("/sms-simulator", include_in_schema=False)
def sms_simulator_page() -> FileResponse:
    return _page("sms_simulator.html")


@router.get("/a11y-audit", include_in_schema=False)
def accessibility_audit_page() -> FileResponse:
    return _page("a11y_audit.html")


@router.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse(url=HOME_PAGE)
