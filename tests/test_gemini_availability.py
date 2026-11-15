"""Phase 4: Gemini quota classification, cooldown, and health honesty."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from assistant.domain.models import ChatStatus, Passage
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider
from assistant.infrastructure.providers.gemini_availability import (
    classify_gemini_failure,
    parse_retry_seconds,
)
from assistant.infrastructure.usage import UsageTracker


def _passage():
    return Passage(
        id="va-1--intro",
        course="VA-1",
        title="VA",
        section="Introduction & Overview",
        anchor="#intro",
        url="/p#intro",
        text="A virtual assistant helps clients remotely.",
        confidence=0.9,
        matched_terms=["virtual", "assistant"],
    )


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Please retry in 2h4m56.266769474s.", 2 * 3600 + 4 * 60 + 56.266769474),
        ("retryDelay': '5941s'", 5941.0),
        ("Please retry in 30s", 30.0),
        ("no hint here", None),
    ],
)
def test_parse_retry_seconds(message, expected):
    got = parse_retry_seconds(message)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected, rel=1e-6)


def test_classify_quota_and_auth():
    class Fake(Exception):
        status_code = 429

    reason, cooldown = classify_gemini_failure(
        Fake("429 RESOURCE_EXHAUSTED. Please retry in 1h0m0s.")
    )
    assert reason == "quota"
    assert cooldown == pytest.approx(3600.0)

    class Auth(Exception):
        status_code = 403

    assert classify_gemini_failure(Auth("PERMISSION_DENIED api key"))[0] == "auth"


def test_quota_failure_does_not_retry_and_sets_cooldown(monkeypatch):
    faq = OfflineFAQProvider()
    usage = UsageTracker()
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq, usage=usage)
    provider.client = MagicMock()
    calls = {"n": 0}

    class QuotaError(Exception):
        status_code = 429

    def boom(*a, **k):
        calls["n"] += 1
        raise QuotaError(
            "429 RESOURCE_EXHAUSTED. Please retry in 10m0s. "
            "{'error': {'details': [{'retryDelay': '600s'}]}}"
        )

    monkeypatch.setattr(provider, "_call_gemini", boom)
    first = provider.generate("What is AI?", [_passage()], "en")
    assert first.fallback_reason == "quota"
    assert first.answer_source == "faq"
    assert calls["n"] == 1
    assert provider.availability.cooling_down()
    status = provider.provider_status()
    assert status["status"] == "quota_cooldown"
    assert status["available"] is False

    # Second question must not call Gemini while cooling down.
    second = provider.generate("What is freelancing?", [_passage()], "en")
    assert second.fallback_reason == "quota"
    assert calls["n"] == 1


def test_health_separates_backend_from_gemini(client):
    body = client.get("/api/health").json()
    assert body["connectivity"]["backend"] == "ok"
    assert "gemini" in body["ai"]
    assert body["ai"]["gemini"]["status"] in (
        "ready", "missing_key", "missing_sdk", "quota_cooldown", "auth_error", "disabled", "unknown",
    )
    assert body["services"]["backend"] == "ok"
    assert "whisper" in body["services"]


def test_health_reports_cloud_gemini_fields_when_configured(tmp_path, monkeypatch):
    from assistant.api.app import create_app
    from assistant.container import build_container
    from assistant.config import get_settings
    from fastapi.testclient import TestClient

    settings = replace(
        get_settings(),
        ai_provider="cloud",
        gemini_api_key="test-key-not-real",
        gemini_model="gemini-2.5-flash",
        enable_exact_cache=False,
        database_path=tmp_path / "health.db",
        chunks_path=tmp_path / "chunks.json",
    )
    # Seed minimal chunks so the container can start.
    from assistant.infrastructure.chunk_store import ChunkStore
    ChunkStore(settings.chunks_path).save([{
        "id": "c--l--a", "scope": "course:va-1", "course": "VA", "lesson_id": "l",
        "title": "VA", "section": "Intro", "anchor": "#a", "url": "/a",
        "text": "Virtual assistants work remotely.",
    }])
    container = build_container(settings)
    app = create_app(container)
    body = TestClient(app).get("/api/health").json()
    assert body["ai"]["provider_setting"] == "cloud"
    assert body["ai"]["gemini"]["configured"] is True
    assert body["ai"]["gemini"]["model"] == "gemini-2.5-flash"
    assert body["ai"]["gemini"]["status"] in ("ready", "missing_sdk")
