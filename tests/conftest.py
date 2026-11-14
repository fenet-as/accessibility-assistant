"""Shared fixtures. Every test run uses a throwaway database and a copy of chunks.json,
so tests never modify the real data in assistant/data/."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TMP_DIR = Path(tempfile.mkdtemp(prefix="alx-assistant-tests-"))
shutil.copy(PROJECT_ROOT / "assistant" / "data" / "chunks.json", _TMP_DIR / "chunks.json")

# Must be set before assistant.config is imported; real env vars beat any local .env.
os.environ.update({
    "AI_PROVIDER": "faq",
    "DATABASE_PATH": str(_TMP_DIR / "test.db"),
    "CHUNKS_PATH": str(_TMP_DIR / "chunks.json"),
    "TELEGRAM_BOT_TOKEN": "",
    "ADMIN_TOKEN": "",
})

from fastapi.testclient import TestClient  # noqa: E402

from assistant.api.app import create_app  # noqa: E402
from assistant.config import load_settings  # noqa: E402
from assistant.container import Container, build_container  # noqa: E402


@pytest.fixture(scope="session")
def container() -> Container:
    return build_container(load_settings())


@pytest.fixture(scope="session")
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))


@pytest.fixture
def anyio_backend():
    return "asyncio"


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
