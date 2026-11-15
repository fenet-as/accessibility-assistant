"""Definition questions must prefer real definition sections, not future-of-industry essays."""

from __future__ import annotations

from dataclasses import replace

from assistant.config import load_settings
from assistant.container import build_container
from assistant.domain.models import ChatRequest, ConversationTurn
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.services.tutor import _definition_boosted, _definition_topic


def test_definition_topic_extraction():
    assert "virtual assistant" in _definition_topic("What is a virtual assistant?")
    assert _definition_topic("what is freelancing") == "freelancing"


def test_definition_boost_prefers_what_is_section(container):
    result = container.tutor.index.retrieve("What is a virtual assistant?", top_k=8, scope="course:va-1")
    boosted = _definition_boosted(list(result.passages), "What is a virtual assistant?")
    assert boosted
    top = boosted[0].section.lower()
    assert "what is a virtual assistant" in top
    assert "future" not in top


def test_faq_answers_va_and_freelancing_distinctly():
    settings = replace(load_settings(), ai_provider="faq", enable_exact_cache=False)
    c = build_container(settings, provider=OfflineFAQProvider())
    va = c.tutor.answer(
        ChatRequest(session="def-1", message="What is a virtual assistant?", language="en", scope="course:va-1")
    )
    assert va.status.value == "answered"
    assert va.citations
    assert va.citations[0].section.lower() == "what is a virtual assistant?"
    assert "profession is not shrinking" not in va.answer.lower()

    hist = [
        ConversationTurn(role="user", content="What is a virtual assistant?"),
        ConversationTurn(role="assistant", content=va.answer),
    ]
    fl = c.tutor.answer(
        ChatRequest(
            session="def-1",
            message="what is freelancing",
            language="en",
            scope="course:va-1",
            history=hist,
        )
    )
    assert fl.status.value == "answered"
    assert fl.citations
    assert "freelanc" in fl.citations[0].section.lower()
    assert fl.answer != va.answer
    assert "profession is not shrinking" not in fl.answer.lower()


def test_not_found_source_type_is_none(client):
    # Force a nonsense course-scoped ask with empty evidence via unrelated token soup
    # still returns a typed response — badge must not claim Gemini when unanswered.
    from assistant.domain.messages import not_found_response
    from assistant.domain.source_meta import apply_response_meta, NONE

    resp = apply_response_meta(not_found_response("en", 0.1), course_id="course:va-1")
    assert resp.source_type == NONE
