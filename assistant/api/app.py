"""FastAPI application factory (Level 2 integration: REST API + OpenAPI at /docs)."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from assistant import __version__
from assistant.api.routers import ALL_ROUTERS
from assistant.channels.sms import SMSAdapter
from assistant.channels.telegram import TelegramAdapter
from assistant.config import PACKAGE_DIR, safe_ai_config_summary
from assistant.container import Container, get_container

WIDGET_DIR = PACKAGE_DIR / "widget"
GZIP_MIN_BYTES = 1024
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "microphone=(self), camera=()")
        return response


def _log_startup_config(container: Container) -> None:
    """Print non-secret AI config so operators can verify .env took effect."""
    settings = container.settings
    summary = safe_ai_config_summary(settings)
    logger.info(
        "Savanna AI config: provider_setting=%s runtime_provider=%s model=%s "
        "gemini_key_configured=%s prefer_extractive=%s exact_cache=%s cache_backend=%s "
        "scope_policy=%s indexed_chunks=%s kb_version=%s",
        summary["ai_provider"],
        container.provider.name,
        summary["gemini_model"],
        summary["gemini_key_configured"],
        summary["prefer_extractive"],
        summary["exact_cache_enabled"],
        container.cache.backend,
        summary["course_scope_policy"],
        container.tutor.indexed_chunks,
        container.tutor.kb_version,
    )
    if settings.ai_provider == "cloud" and not summary["gemini_key_configured"]:
        logger.warning(
            "AI_PROVIDER=cloud but GEMINI_API_KEY is empty — answers will use FAQ fallback only"
        )


def create_app(container: Optional[Container] = None) -> FastAPI:
    container = container or get_container()
    settings = container.settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _log_startup_config(container)
        yield

    app = FastAPI(
        title="ALX Accessibility Assistant API",
        description="Multilingual, grounded AI tutor and Career Gateway API for Ethiopian learners.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.container = container
    app.state.sms = SMSAdapter(container)
    app.state.telegram = TelegramAdapter(container)

    # Credentials stay off: the widget is embedded cross-origin and sends no cookies.
    # Production should set CORS_ORIGINS to explicit LMS origins (not *).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Learners on 3G: compress JSON and the widget script.
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_BYTES)
    app.add_middleware(SecurityHeadersMiddleware)

    for router in ALL_ROUTERS:
        app.include_router(router)

    app.mount("/widget", StaticFiles(directory=WIDGET_DIR), name="widget")
    app.mount("/assistant/widget", StaticFiles(directory=WIDGET_DIR), name="assistant_widget")
    if settings.savanna_dir.exists():
        app.mount("/savanna", StaticFiles(directory=settings.savanna_dir, html=True), name="savanna")

    return app
