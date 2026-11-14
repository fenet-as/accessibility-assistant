"""Milestone 4: provider routing, exact-answer cache, invalidation and usage accounting."""

from dataclasses import replace

import pytest

from assistant.config import load_settings
from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.answer_cache import AnswerCache, cache_key_parts, is_cacheable
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers import OfflineFAQProvider, build_provider
from assistant.infrastructure.providers.composite import RoutedAIProvider
from assistant.infrastructure.providers.routing import prefers_extractive_answer
from assistant.infrastructure.usage import UsageTracker
from assistant.services.tutor import TutorService


@pytest.fixture
def tutor_with_cache(container):
    return container.tutor


def test_provider_faq_mode_is_offline_faq(container):
    settings = replace(container.settings, ai_provider="faq")
    provider = build_provider(settings, usage=UsageTracker())
    assert provider.name == "offline_faq"


def test_provider_cloud_mode_is_routed(container):
    settings = replace(container.settings, ai_provider="cloud", gemini_api_key="")
    provider = build_provider(settings, usage=UsageTracker())
    assert isinstance(provider, RoutedAIProvider)


def test_exact_answer_cache_hit_skips_second_provider_call(container):
    settings = replace(container.settings, enable_exact_cache=True)
    usage = UsageTracker()
    provider = OfflineFAQProvider(settings.faq_translations_path)

    class CountingFAQ(OfflineFAQProvider):
        def __init__(self):
            super().__init__(settings.faq_translations_path)
            self.calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            return super().generate(*args, **kwargs)

    counter = CountingFAQ()
    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        counter,
        settings.relevance_threshold,
        cache=AnswerCache(settings),
        usage=usage,
        settings=settings,
    )
    message = "What is shaping the future of VA work?"
    first = tutor.answer(ChatRequest(message=message, language="en", scope="course:va-1"))
    second = tutor.answer(ChatRequest(message=message, language="en", scope="course:va-1"))
    assert first.status == ChatStatus.ANSWERED
    assert second.cache_hit is True
    assert second.answer_source == "cache"
    assert counter.calls == 1
    assert usage.snapshot()["cache_hits"] == 1
    assert usage.snapshot()["cache_misses"] == 1


def test_cache_key_changes_when_kb_version_changes():
    base = cache_key_parts(
        scope="course:va-1", language="en", question="Hello", simple=False,
        kb_version="abc", model_version="faq",
    )
    other = cache_key_parts(
        scope="course:va-1", language="en", question="Hello", simple=False,
        kb_version="def", model_version="faq",
    )
    assert base != other


def test_not_cacheable_without_citations():
    from assistant.domain.models import ChatResponse

    response = ChatResponse(
        status=ChatStatus.ANSWERED,
        language="en",
        answer="Text",
        citations=[],
    )
    assert is_cacheable(response, ("Section",)) is False


def test_prefers_extractive_on_high_confidence_definitional():
    from assistant.domain.models import Passage

    passage = Passage(
        id="x", course="c", title="t", section="Introduction", anchor="#a", url="/u",
        text="body", confidence=0.95,
    )
    assert prefers_extractive_answer("What is a virtual assistant?", [passage], confidence=0.9, simple=False)


def test_cache_disabled_calls_provider_twice(container):
    settings = replace(container.settings, enable_exact_cache=False)
    counter_calls = {"n": 0}

    class CountingFAQ(OfflineFAQProvider):
        def generate(self, *args, **kwargs):
            counter_calls["n"] += 1
            return super().generate(*args, **kwargs)

    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        CountingFAQ(settings.faq_translations_path),
        settings.relevance_threshold,
        cache=AnswerCache(settings),
        settings=settings,
    )
    msg = "What is shaping the future of VA work?"
    tutor.answer(ChatRequest(message=msg))
    tutor.answer(ChatRequest(message=msg))
    assert counter_calls["n"] == 2


def test_cloud_without_key_still_answers(container):
    settings = replace(load_settings(), ai_provider="cloud", gemini_api_key="", enable_exact_cache=False)
    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        build_provider(settings),
        settings.relevance_threshold,
        settings=settings,
    )
    assert tutor.answer(ChatRequest(message="What is shaping the future of VA work?")).status == ChatStatus.ANSWERED