"""Phase 1: AI config transparency, cache clear, honest fallback labels."""

from dataclasses import replace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from assistant.api.app import create_app
from assistant.config import safe_ai_config_summary
from assistant.container import build_container
from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.answer_cache import AnswerCache
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider
from assistant.services.tutor import TutorService


def test_safe_ai_config_summary_hides_secrets(container):
    summary = safe_ai_config_summary(container.settings)
    assert "ai_provider" in summary
    assert "gemini_model" in summary
    assert "gemini_key_configured" in summary
    assert "GEMINI_API_KEY" not in str(summary)
    assert "api_key" not in str(summary).lower() or "configured" in str(summary).lower()
    blob = str(summary)
    assert container.settings.gemini_api_key not in blob if container.settings.gemini_api_key else True


def test_health_and_config_expose_model_without_secrets(client):
    health = client.get("/api/health").json()
    assert "ai" in health
    assert health["ai"]["gemini"]["model"]
    assert "config" in health["ai"]
    assert "restart_required" in health["ai"]["config"]["note"].lower() or "Restart" in health["ai"]["config"]["note"]

    cfg = client.get("/api/config").json()
    assert cfg["ai"]["provider_setting"]
    assert cfg["ai"]["runtime_provider"]
    assert cfg["restart_required_after_env_change"] is True
    assert "api_key" not in str(cfg).lower() or "configured" in str(cfg).lower()


def test_admin_cache_clear(container):
    settings = replace(container.settings, enable_exact_cache=True, allow_open_admin=True, admin_token="")
    app = create_app(build_container(settings))
    client = TestClient(app)
    cache = app.state.container.cache
    from assistant.domain.models import ChatResponse, Citation

    key = cache.make_key(
        scope="course:va-1", language="en", question="ping", simple=False,
        kb_version="v1", model_version="faq|course", history_fp="",
    )
    cache.set(
        key,
        ChatResponse(
            status=ChatStatus.ANSWERED, language="en", answer="cached",
            citations=[Citation(title="t", section="S", url="/x")], answer_source="faq",
        ),
        question="ping", scope="course:va-1", kb_version="v1", model_version="faq|course",
    )
    assert cache.get(key) is not None
    res = client.post("/api/admin/cache/clear")
    assert res.status_code == 200
    assert res.json()["status"] == "cleared"
    assert cache.get(key) is None


def test_gemini_fallback_never_claims_cloud_source(container, monkeypatch):
    faq = OfflineFAQProvider(container.settings.faq_translations_path)
    provider = GeminiProvider("fake-key", "gemini-test-model", faq)
    provider.client = MagicMock()

    def _boom(*a, **k):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr(provider, "_call_gemini", _boom)
    settings = replace(container.settings, enable_exact_cache=False)
    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        provider,
        settings.relevance_threshold,
        settings=settings,
    )
    res = tutor.answer(ChatRequest(
        message="What is shaping the future of VA work?",
        language="en",
        scope="course:va-1",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.fallback_reason
    assert res.answer_source == "faq"
    assert res.provider == "offline_faq"
    assert res.source_type == "faq"
