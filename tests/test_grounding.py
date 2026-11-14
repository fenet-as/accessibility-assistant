"""Grounded answers, citations, the rejection rule, and the answer cache."""

from dataclasses import replace

import pytest

from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers import GeminiProvider, OfflineFAQProvider, build_provider
from assistant.services.tutor import TutorService


@pytest.fixture
def tutor(container):
    return container.tutor


@pytest.mark.parametrize("question, expected_section", [
    ("What is shaping the future of virtual assistant work?", "What is Shaping the Future"),
    ("How can AI tools support virtual assistants?", "Artificial Intelligence"),
    ("Where do human virtual assistants still add the most value?", "Artificial Intelligence"),
    ("What will clients value more and more in a VA?", "What Clients Are Likely to Value"),
    ("What does this mean for aspiring virtual assistants?", "What This Means for Aspiring"),
    ("Is the future of the VA industry promising?", "So, is the Future of VA Promising"),
    ("What is the difference between an AI assistant and human VA?", "Introduction & Overview"),
])
def test_in_scope_english(tutor, question, expected_section):
    res = tutor.answer(ChatRequest(message=question))
    assert res.status == ChatStatus.ANSWERED
    assert res.language == "en"
    assert any(expected_section in c.section for c in res.citations)


@pytest.mark.parametrize("question, expected_section", [
    ("ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ላይ ያለው ሚና ምንድን ነው?", "Artificial Intelligence"),
    ("የቨርቹዋል ረዳት (VA) ሥራ ወደፊት ምን ይመስላል?", "What is Shaping the Future"),
    ("ደንበኞች ከቨርቹዋል ረዳቶች ምን ዓይነት ክህሎቶችን ይፈልጋሉ?", "What Clients Are Likely to Value"),
])
def test_in_scope_amharic(tutor, question, expected_section):
    res = tutor.answer(ChatRequest(message=question))
    assert res.status == ChatStatus.ANSWERED
    assert res.language == "am"
    assert any(expected_section in c.section for c in res.citations)


@pytest.mark.parametrize("question", [
    "How do I bake a chocolate cake?",
    "What is the capital of France?",
    "Who won the 2022 World Cup?",
    "How do I repair a bicycle tyre?",
    "የስንዴ ዳቦ አዘገጃጀት እንዴት ነው?",
])
def test_out_of_scope_is_rejected(tutor, question):
    res = tutor.answer(ChatRequest(message=question))
    assert res.status == ChatStatus.NOT_FOUND
    assert res.citations == []
    assert "get_human_help" in res.actions


def test_simple_mode_is_shorter(tutor):
    question = "What are the key trends in virtual assistant work?"
    normal = tutor.answer(ChatRequest(message=question, mode="normal"))
    simple = tutor.answer(ChatRequest(message=question, mode="simple"))
    assert normal.status == simple.status == ChatStatus.ANSWERED
    assert len(simple.answer) <= len(normal.answer)


def test_cloud_provider_without_key_falls_back_to_offline(container):
    provider = build_provider(replace(container.settings, ai_provider="cloud", gemini_api_key=""))
    assert isinstance(provider, GeminiProvider)
    tutor = TutorService(ChunkStore(container.settings.chunks_path), provider)
    assert tutor.answer(ChatRequest(message="What is shaping the future of VA work?")).status == ChatStatus.ANSWERED


class CountingProvider(OfflineFAQProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        return super().generate(*args, **kwargs)


def test_repeated_questions_are_served_from_cache(container):
    provider = CountingProvider()
    tutor = TutorService(ChunkStore(container.settings.chunks_path), provider)

    for text in ["What is shaping the future of VA work?", "  what is shaping the future of va work?  "]:
        assert tutor.answer(ChatRequest(message=text)).status == ChatStatus.ANSWERED
    assert provider.calls == 1


def test_index_reloads_when_another_worker_changes_the_corpus(container, tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save(ChunkStore(container.settings.chunks_path).load())
    worker_a = TutorService(store, OfflineFAQProvider())
    worker_b = TutorService(ChunkStore(store.path), OfflineFAQProvider())

    question = ChatRequest(message="How does photosynthesis convert sunlight?", scope="course:bio")
    assert worker_a.answer(question).status == ChatStatus.NOT_FOUND

    worker_b.store.replace_course("course:bio", [{
        "id": "bio-1", "course": "Biology", "scope": "course:bio", "title": "Biology",
        "section": "Photosynthesis", "anchor": "#photosynthesis", "url": "/bio#photosynthesis",
        "text": "Photosynthesis lets plants convert sunlight, water and carbon dioxide into sugar.",
    }])
    assert worker_a.answer(question).status == ChatStatus.ANSWERED
