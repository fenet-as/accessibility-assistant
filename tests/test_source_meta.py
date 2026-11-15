"""Phase 7: response source_type / connectivity / course_id metadata."""

from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, Citation
from assistant.domain.source_meta import (
    CACHE,
    CAREERS,
    CONNECTIVITY_ONLINE,
    COURSE_GROUNDED,
    FAQ,
    GENERAL_KNOWLEDGE,
    MIXED,
    SOCIAL,
    apply_response_meta,
    resolve_source_type,
)


def test_resolve_source_type_variants():
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="Hi", answer_source="social",
    )) == SOCIAL
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="Jobs", provider="careers", answer_source="careers",
    )) == CAREERS
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="A", answer_source="cloud_general",
    )) == GENERAL_KNOWLEDGE
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="From the lesson…", answer_source="cloud",
        citations=[Citation(title="t", section="Intro", url="/x")],
    )) == COURSE_GROUNDED
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en",
        answer="Course text.\n\n## General explanation\nExtra tips.",
        answer_source="cloud",
        citations=[Citation(title="t", section="Intro", url="/x")],
    )) == MIXED
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="Extract", answer_source="faq",
    )) == FAQ
    assert resolve_source_type(ChatResponse(
        status=ChatStatus.ANSWERED, language="en", answer="Cached", answer_source="faq", cache_hit=True,
    )) == CACHE


def test_tutor_responses_include_phase7_metadata(container):
    tutor = container.tutor
    answered = tutor.answer(ChatRequest(
        message="What is shaping the future of VA work?",
        language="en",
        scope="course:va-1",
    ))
    assert answered.status == ChatStatus.ANSWERED
    assert answered.course_id == "course:va-1"
    assert answered.connectivity == CONNECTIVITY_ONLINE
    assert answered.source_type in (FAQ, COURSE_GROUNDED, CACHE)
    assert answered.answer_source  # compatibility field still set

    greeting = tutor.answer(ChatRequest(message="Hello!", language="en", scope="course:va-1"))
    assert greeting.source_type == SOCIAL
    assert greeting.course_id == "course:va-1"


def test_apply_response_meta_sets_fields():
    response = ChatResponse(
        status=ChatStatus.ANSWERED,
        language="en",
        answer="ok",
        answer_source="faq",
        provider="offline_faq",
    )
    apply_response_meta(response, course_id="course:va-1", connectivity=CONNECTIVITY_ONLINE)
    assert response.course_id == "course:va-1"
    assert response.connectivity == CONNECTIVITY_ONLINE
    assert response.source_type == FAQ
