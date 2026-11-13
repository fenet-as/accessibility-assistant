"""Tests for Grounded RAG Pipeline, Citations, and Anti-Hallucination Rejection."""

import pytest
from assistant.core.models import ChatRequest, ChatStatus
from assistant.core.grounding import GroundingEngine


@pytest.fixture
def engine():
    return GroundingEngine()


def test_in_scope_english_suite(engine):
    """Verify 7 in-scope English questions retrieve and cite the correct sections."""
    test_cases = [
        ("What is shaping the future of virtual assistant work?", "What is Shaping the Future"),
        ("How can AI tools support virtual assistants?", "Artificial Intelligence"),
        ("Where do human virtual assistants still add the most value?", "Artificial Intelligence"),
        ("What will clients value more and more in a VA?", "What Clients Are Likely to Value"),
        ("What does this mean for aspiring virtual assistants?", "What This Means for Aspiring"),
        ("Is the future of the VA industry promising?", "So, is the Future of VA Promising"),
        ("What is the difference between an AI assistant and human VA?", "Introduction & Overview")
    ]

    for question, expected_section in test_cases:
        res = engine.process_query(ChatRequest(message=question))
        assert res.status == ChatStatus.ANSWERED, f"Expected ANSWERED for: {question}"
        assert res.language == "en"
        assert len(res.citations) > 0
        section_titles = [c.section for c in res.citations]
        assert any(expected_section in s for s in section_titles), (
            f"Expected section '{expected_section}' for '{question}', got {section_titles}"
        )


def test_in_scope_amharic_suite(engine):
    """Verify 3 in-scope Amharic questions retrieve correctly and answer in Amharic."""
    amharic_cases = [
        ("ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ላይ ያለው ሚና ምንድን ነው?", "Artificial Intelligence"),
        ("የቨርቹዋል ረዳት (VA) ሥራ ወደፊት ምን ይመስላል?", "What is Shaping the Future"),
        ("ደንበኞች ከቨርቹዋል ረዳቶች ምን ዓይነት ክህሎቶችን ይፈልጋሉ?", "What Clients Are Likely to Value")
    ]

    for question, expected_section in amharic_cases:
        res = engine.process_query(ChatRequest(message=question))
        assert res.status == ChatStatus.ANSWERED, f"Expected ANSWERED for: {question}"
        assert res.language == "am", f"Expected language 'am' for: {question}"
        assert len(res.citations) > 0
        section_titles = [c.section for c in res.citations]
        assert any(expected_section in s for s in section_titles)


def test_strict_out_of_scope_rejection(engine):
    """Irrelevant questions must strictly return NOT_FOUND with NO hallucinations."""
    out_of_scope_questions = [
        "How do I bake a chocolate cake?",
        "What is the capital of France?",
        "Who won the 2022 World Cup?",
        "How do I repair a bicycle tyre?",
        "የስንዴ ዳቦ አዘገጃጀት እንዴት ነው?"
    ]

    for q in out_of_scope_questions:
        req = ChatRequest(message=q)
        res = engine.process_query(req)

        assert res.status == ChatStatus.NOT_FOUND, f"Failed for query: {q}"
        assert len(res.citations) == 0, f"Expected 0 citations for out-of-scope question: {q}"
        assert "get_human_help" in res.actions


def test_simple_mode(engine):
    """Simple mode should produce grounded, shorter text."""
    req_normal = ChatRequest(
        message="What are the key trends in virtual assistant work?",
        mode="normal"
    )
    req_simple = ChatRequest(
        message="What are the key trends in virtual assistant work?",
        mode="simple"
    )

    res_normal = engine.process_query(req_normal)
    res_simple = engine.process_query(req_simple)

    assert res_normal.status == ChatStatus.ANSWERED
    assert res_simple.status == ChatStatus.ANSWERED
    assert len(res_simple.answer) <= len(res_normal.answer)
