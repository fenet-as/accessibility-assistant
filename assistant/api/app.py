"""FastAPI application factory (Level 2 integration: REST API + OpenAPI at /docs)."""

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from assistant import __version__
from assistant.api.routers import ALL_ROUTERS
from assistant.channels.sms import SMSAdapter
from assistant.channels.telegram import TelegramAdapter
from assistant.config import PACKAGE_DIR
from assistant.container import Container, get_container

WIDGET_DIR = PACKAGE_DIR / "widget"
GZIP_MIN_BYTES = 1024


def create_app(container: Optional[Container] = None) -> FastAPI:
    container = container or get_container()
    settings = container.settings

    app = FastAPI(
        title="ALX Accessibility Assistant API",
        description="Multilingual, grounded AI tutor and Career Gateway API for Ethiopian learners.",
        version=__version__,
    )
    app.state.container = container
    app.state.sms = SMSAdapter(container)
    app.state.telegram = TelegramAdapter(container)

    # Credentials stay off: the widget is embedded cross-origin and sends no cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Learners on 3G: compress JSON and the widget script.
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_BYTES)

    for router in ALL_ROUTERS:
        app.include_router(router)

    app.mount("/widget", StaticFiles(directory=WIDGET_DIR), name="widget")
    app.mount("/assistant/widget", StaticFiles(directory=WIDGET_DIR), name="assistant_widget")
    if settings.savanna_dir.exists():
        app.mount("/savanna", StaticFiles(directory=settings.savanna_dir, html=True), name="savanna")

    return app
