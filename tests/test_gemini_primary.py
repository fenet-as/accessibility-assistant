"""Milestone 5: Gemini primary routing, timeout/retry, citation fallback."""

from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from assistant.domain.models import ChatResponse, ChatStatus, Passage
from assistant.infrastructure.providers.composite import RoutedAIProvider
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider, validate_citations
from assistant.infrastructure.usage import UsageTracker


def _passage(section="Introduction & Overview"):
    return Passage(
        id="va-1--intro",
        course="VA-1",
        title="VA",
        section=section,
        anchor="#intro",
        url="/p#intro",
        text="A virtual assistant helps clients with remote administrative work every day.",
        confidence=0.9,
        matched_terms=["virtual", "assistant"],
    )


class _BoomGemini:
    name = "cloud_gemini"

    def __init__(self, fallback, reason="error"):
        self.fallback = fallback
        self.reason = reason
        self.calls = 0

    def generate(self, question, passages, language, simple=False, history=None, *, confidence=0.0):
        self.calls += 1
        response = self.fallback.generate(question, passages, language, simple, history=history, confidence=confidence)
        response.fallback_reason = self.reason
        response.answer_source = "faq"
        return response


def test_routed_provider_calls_gemini_first_by_default():
    faq = OfflineFAQProvider()
    generative = MagicMock()
    generative.name = "cloud_gemini"
    generative.generate.return_value = ChatResponse(
        status=ChatStatus.ANSWERED,
        language="en",
        answer="Direct answer from Gemini about virtual assistants.",
        citations=[],
        answer_source="cloud",
        provider="cloud_gemini",
    )
    routed = RoutedAIProvider(faq, generative, prefer_extractive=False)
    response = routed.generate("What is a virtual assistant?", [_passage()], "en", confidence=0.95)
    assert generative.generate.called
    assert response.answer_source == "cloud"


def test_gemini_timeout_falls_back_with_reason(monkeypatch):
    faq = OfflineFAQProvider()
    usage = UsageTracker()
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq, timeout_seconds=0.01, usage=usage)
    provider.client = MagicMock()

    def _hang(*a, **k):
        raise FuturesTimeout()

    monkeypatch.setattr(provider, "_call_gemini", _hang)
    response = provider.generate("What is AI?", [_passage()], "en")
    assert response.fallback_reason == "timeout"
    assert response.answer_source == "faq"
    assert usage.snapshot()["fallbacks"] >= 1


def test_gemini_answer_without_named_section_keeps_empty_citations(monkeypatch):
    faq = OfflineFAQProvider()
    usage = UsageTracker()
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq, usage=usage)
    provider.client = MagicMock()

    fake = MagicMock()
    fake.text = "Totally invented answer with no section title."

    monkeypatch.setattr(provider, "_call_gemini", lambda *a, **k: fake)
    response = provider.generate("What is AI?", [_passage()], "en")
    assert response.status == ChatStatus.ANSWERED
    assert response.citations == []
    assert response.answer_source == "cloud"
    assert response.fallback_reason is None


def test_gemini_general_mode_answers_without_passages(monkeypatch):
    faq = OfflineFAQProvider()
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq)
    provider.client = MagicMock()
    fake = MagicMock()
    fake.text = "A professional portfolio shows sample work, tools you know, and client results."
    monkeypatch.setattr(provider, "_call_gemini", lambda *a, **k: fake)
    response = provider.generate(
        "How do I create a professional portfolio?", [], "en", answer_mode="general"
    )
    assert response.status == ChatStatus.ANSWERED
    assert response.citations == []
    assert response.answer_source == "cloud_general"


def test_gemini_general_mode_out_of_scope_sentinel(monkeypatch):
    faq = OfflineFAQProvider()
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq)
    provider.client = MagicMock()
    fake = MagicMock()
    fake.text = "OUT_OF_SCOPE"
    monkeypatch.setattr(provider, "_call_gemini", lambda *a, **k: fake)
    response = provider.generate("Who won the match?", [], "en", answer_mode="general")
    assert response.status == ChatStatus.OUT_OF_SCOPE


def test_validate_citations_allows_empty_and_rejects_nothing_from_passages():
    from assistant.infrastructure.providers.gemini import cited_passages

    passages = [_passage("Introduction & Overview")]
    assert validate_citations("See Introduction & Overview for details.", passages)
    assert cited_passages("See Introduction & Overview for details.", passages)
    # No invented default citation when the model names no section.
    assert cited_passages("A helpful general answer with no section title.", passages) == []
    assert validate_citations("A helpful general answer with no section title.", passages)


@pytest.mark.live
def test_live_gemini_grounded_answers(container):
    import os

    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    # Opt-in: the free tier is 20 requests/day; normal pytest runs must not burn it.
    if os.environ.get("RUN_LIVE_GEMINI", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_LIVE_GEMINI=1 to hit the live Gemini API")
    settings = replace(container.settings, ai_provider="cloud", gemini_api_key=os.environ["GEMINI_API_KEY"])
    from assistant.infrastructure.providers import build_provider
    from assistant.services.tutor import TutorService
    from assistant.domain.models import ChatRequest

    tutor = TutorService(container.courses.store, build_provider(settings, usage=UsageTracker()), settings=settings)
    response = tutor.answer(ChatRequest(message="What is a virtual assistant?", language="en", scope="course:va-1"))
    assert response.status in (ChatStatus.ANSWERED, ChatStatus.NOT_FOUND)
    if response.status == ChatStatus.ANSWERED and response.answer_source == "cloud":
        # Course-grounded answers may cite; general/FAQ fallbacks may not.
        assert response.provider
