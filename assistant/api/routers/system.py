"""Health, analytics data and the server-rendered HTML tools (dashboards, simulator, audit)."""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse

from assistant import __version__
from assistant.api.dependencies import get_container
from assistant.config import safe_ai_config_summary
from assistant.container import Container
from assistant.domain.language import AUTO, SUPPORTED_LANGUAGES, UI_STRINGS, language_catalog
from assistant.infrastructure.answer_cache import PROMPT_VERSION
from assistant.infrastructure.speech import stt_status

PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"
HOME_PAGE = "/savanna/pages/concept-with-navigation.html"

router = APIRouter()


def _page(name: str) -> FileResponse:
    return FileResponse(PAGES_DIR / name, media_type="text/html")


def _ai_health(container: Container) -> Dict[str, Any]:
    """Connectivity of the backend is not the same as Gemini or Whisper availability."""
    settings = container.settings
    provider = container.provider
    status = provider.provider_status() if hasattr(provider, "provider_status") else {"name": provider.name}
    generative = status.get("generative") if isinstance(status.get("generative"), dict) else status
    gemini_configured = bool((settings.gemini_api_key or "").strip())
    # When AI_PROVIDER is not cloud, Gemini may still be configured but unused.
    if settings.ai_provider == "cloud":
        gemini = {
            "configured": gemini_configured,
            "sdk_loaded": bool(generative.get("sdk_loaded")) if generative else False,
            "model": settings.gemini_model,
            "available": bool(generative.get("available")) if generative else False,
            "status": generative.get("status", "unknown") if generative else "unknown",
            "cooldown_until": generative.get("cooldown_until") if generative else None,
            "cooldown_remaining_seconds": generative.get("cooldown_remaining_seconds", 0) if generative else 0,
            "last_failure_reason": generative.get("last_failure_reason") if generative else None,
        }
    else:
        gemini = {
            "configured": gemini_configured,
            "sdk_loaded": False,
            "model": settings.gemini_model,
            "available": False,
            "status": "disabled",
            "cooldown_until": None,
            "cooldown_remaining_seconds": 0,
            "last_failure_reason": None,
        }
    return {
        "provider_setting": settings.ai_provider,
        "runtime_provider": container.provider.name,
        "prefer_extractive": bool(settings.prefer_extractive),
        "prompt_version": PROMPT_VERSION,
        # Kept for older clients; prefer gemini.available for readiness checks.
        "gemini_configured": gemini_configured,
        "gemini": gemini,
        "provider": status,
        "config": safe_ai_config_summary(settings),
        "cache": {
            "enabled": settings.enable_exact_cache,
            "prompt_version": PROMPT_VERSION,
            **container.cache.size_hint(),
        },
    }


@router.get("/api/health", tags=["System"])
def health(container: Container = Depends(get_container)) -> Dict[str, Any]:
    speech = stt_status(container.settings)
    ai = _ai_health(container)
    return {
        "status": "healthy",
        "provider": container.provider.name,
        "indexed_chunks": container.tutor.indexed_chunks,
        "kb_version": container.tutor.kb_version,
        "languages": list(SUPPORTED_LANGUAGES),
        "version": __version__,
        "cache_backend": container.cache.backend,
        "exact_cache_enabled": container.settings.enable_exact_cache,
        "usage": container.usage.snapshot(),
        "speech": speech,
        "rate_limit": container.rate_limiter.status(),
        # Backend answered this request. Browser online/offline is a client concern.
        "connectivity": {
            "backend": "ok",
            "internet": None,
            "note": (
                "backend=ok means this API is reachable. "
                "Browser online state and Gemini/Whisper availability are separate."
            ),
        },
        "ai": ai,
        "services": {
            "backend": "ok",
            "gemini": ai["gemini"]["status"],
            "whisper": "ready" if speech.get("server_stt") else "unavailable",
            "cache": container.cache.backend,
        },
    }


@router.get("/api/usage", tags=["System"])
def usage_stats(container: Container = Depends(get_container)) -> Dict[str, Any]:
    """AI token and cache counters for operators (aggregated, no learner text)."""
    return {
        "provider": container.provider.name,
        "cache_backend": container.cache.backend,
        "exact_cache_enabled": container.settings.enable_exact_cache,
        **container.usage.snapshot(),
    }


@router.get("/api/config", tags=["System"])
def public_config(container: Container = Depends(get_container)) -> Dict[str, Any]:
    """Safe AI/runtime configuration for operators and the widget (never includes API keys)."""
    ai = _ai_health(container)
    return {
        "version": __version__,
        "ai": ai,
        "kb_version": container.tutor.kb_version,
        "indexed_chunks": container.tutor.indexed_chunks,
        "languages": list(SUPPORTED_LANGUAGES),
        "restart_required_after_env_change": True,
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
