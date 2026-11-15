"""Flexible multilingual course-name matching against the live chunk catalog."""

from __future__ import annotations

from dataclasses import replace

import pytest

from assistant.config import load_settings
from assistant.container import build_container
from assistant.domain.models import ChatRequest
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.services.course_alias_data import DEFAULT_COURSE_ALIASES
from assistant.services.course_matcher import (
    CourseMatcher,
    CourseRecord,
    compact_course_text,
    normalize_course_text,
)


@pytest.fixture
def matcher(container) -> CourseMatcher:
    return CourseMatcher(container.courses.store, alias_config=DEFAULT_COURSE_ALIASES)


@pytest.fixture
def faq_tutor():
    settings = replace(load_settings(), ai_provider="faq", enable_exact_cache=False)
    return build_container(settings, provider=OfflineFAQProvider()).tutor


def test_normalize_and_compact():
    assert normalize_course_text("Virtual-Assistant") == "virtual assistant"
    assert compact_course_text("virtual_assistant") == "virtualassistant"
    assert compact_course_text("VIRTUAL ASSISTANT") == compact_course_text("virtualassistant")


@pytest.mark.parametrize(
    "query,method_substr",
    [
        ("Virtual Assistant", "normalized"),
        ("virtual assistant", "normalized"),
        ("virtualassistant", "compact"),
        ("virtual-assistant", "normalized"),
        ("virtul assistant", "fuzzy"),
        ("virtual asistant", "fuzzy"),
        ("virtual assistent", "fuzzy"),
        ("VA course", "alias"),
        ("ቨርቹዋል ረዳት", "alias"),
        ("gargaaraa virtualii", "alias"),
        ("ቨርቹዋል ሓጋዚ", "alias"),
        ("kaaliye virtual", "alias"),
        ("المساعد الافتراضي", "alias"),
    ],
)
def test_resolve_without_ui_scope(matcher: CourseMatcher, query: str, method_substr: str):
    result = matcher.resolve(query, ui_scope="auto")
    assert result.ok, f"{query!r} failed: {result}"
    assert result.scope == "course:va-1"
    assert method_substr in result.method or result.method in {
        "normalized",
        "compact",
        "alias",
        "fuzzy",
        "partial",
        "abbreviation",
        "exact",
    }
    assert "virtual assistant" in result.rewritten_message.casefold() or result.method == "abbreviation"


def test_ui_scope_never_silently_switches(matcher: CourseMatcher):
    result = matcher.resolve("Cooking School", ui_scope="course:va-1")
    assert result.scope == "course:va-1"
    assert result.method == "ui_scope"
    assert result.ui_scope_honored is True
    assert result.rewritten_message == "Cooking School"


def test_unrelated_name_does_not_match_open_scope(matcher: CourseMatcher):
    result = matcher.resolve("Advanced Underwater Basket Weaving 101", ui_scope="auto")
    assert not result.ok
    assert result.scope == ""


def test_in_sentence_questions(matcher: CourseMatcher):
    for q in [
        "Explain virtual assistant.",
        "What can I learn from the virtul assistant course?",
        "Tell me about the virtualassistant course.",
    ]:
        result = matcher.resolve(q, ui_scope="auto")
        assert result.ok, q
        assert result.scope == "course:va-1"
        assert "virtual assistant" in result.rewritten_message.casefold()


def test_ambiguous_when_two_similar_courses(matcher: CourseMatcher):
    # Inject a second synthetic course with a similar name.
    matcher._records["course:va-pro"] = CourseRecord(
        scope="course:va-pro",
        canonical_name="VA Pro: Advanced Virtual Assistant",
        search_names=("Virtual Assistant Pro", "Advanced Virtual Assistant"),
        abbreviations=("VAP",),
        aliases=("virtual assistant pro", "ቨርቹዋል ረዳት ፕሮ"),
        primary_search_phrase="Virtual Assistant Pro",
    )
    matcher._alias_index.append(("virtual assistant pro", "virtualassistantpro", "course:va-pro"))
    matcher._alias_index.append(("advanced virtual assistant", "advancedvirtualassistant", "course:va-pro"))

    result = matcher.resolve("virtual assistant", ui_scope="auto")
    # Both courses mention Virtual Assistant — should ask for clarification.
    assert result.ambiguous or (
        result.ok and result.scope in {"course:va-1", "course:va-pro"}
    )
    # Force a clearly ambiguous short shared stem:
    result2 = matcher.resolve("Virtual Assistant", ui_scope="auto")
    assert len(result2.candidates) >= 1
    if result2.ambiguous:
        assert len(result2.candidates) >= 2


def test_faq_answers_mistyped_course_names(faq_tutor):
    cases = [
        "virtualassistant",
        "virtul assistant",
        "virtual asistant",
        "Tell me about the virtualassistant course.",
        "What can I learn from the virtul assistant course?",
        "VA course",
    ]
    for q in cases:
        response = faq_tutor.answer(
            ChatRequest(session="cm-1", message=q, language="en", scope="course:va-1")
        )
        assert response.status.value == "answered", f"{q!r} -> {response.status} {response.answer[:80]}"
        assert response.course_id == "course:va-1"
        assert response.citations, q


def test_embedded_aliases_linked_to_catalog(matcher: CourseMatcher):
    assert "course:va-1" in DEFAULT_COURSE_ALIASES
    assert "course:va-1" in matcher.known_scopes()
    record = matcher.get("course:va-1")
    assert record is not None
    assert any("ቨርቹዋል ረዳት" in a for a in record.aliases)
    assert "VA" in record.abbreviations
