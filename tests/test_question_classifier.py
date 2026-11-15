"""Question classification and hybrid routing: retrieval confidence is evidence, not a verdict."""

import pytest

from assistant.config import Settings
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.services.question_classifier import (
    QuestionType,
    ScopePolicy,
    classify,
    read_signals,
    refers_back,
    strip_course_meta,
    strip_language_switch,
)
from assistant.services.tutor import TutorService

FREELANCING_HISTORY = [
    ConversationTurn(role="user", content="What is freelancing?"),
    ConversationTurn(role="assistant", content="Freelancing means working independently for clients."),
]


def kind(message, history=(), *, confidence=0.0, text_language="en", policy=ScopePolicy.EDUCATION):
    signals = read_signals(message, list(history))
    return classify(signals, text_language=text_language, course_confidence=confidence, policy=policy)


@pytest.mark.parametrize("message", [
    "What is freelancing?",
    "Where do virtual assistants work?",
    "What skills does a virtual assistant need?",
    "What is the difference between freelancing and remote employment?",
    "How do I create a professional portfolio?",
])
def test_in_scope_questions_are_never_unrelated_even_without_course_evidence(message):
    assert kind(message).type in (QuestionType.GENERAL, QuestionType.CAREER)


def test_career_guidance_is_its_own_type():
    assert kind("How can I become a freelancer?").type == QuestionType.CAREER


@pytest.mark.parametrize("message", [
    "What is photosynthesis?", "Who won the 2022 World Cup?", "How do I bake a chocolate cake?",
])
def test_off_topic_english_questions_are_unrelated(message):
    assert kind(message).type == QuestionType.UNRELATED


def test_open_policy_never_declines():
    assert kind("What is photosynthesis?", policy=ScopePolicy.OPEN).type == QuestionType.GENERAL


def test_scope_is_left_unconfirmed_for_text_the_vocabulary_cannot_judge():
    result = kind("የስንዴ ዳቦ አዘገጃጀት እንዴት ነው?", text_language="am")
    assert result.type == QuestionType.GENERAL and result.scope_confirmed is False


def test_strong_course_evidence_or_explicit_course_reference_is_a_course_question():
    assert kind("How does a while loop work?", confidence=0.9).type == QuestionType.COURSE
    assert kind("What did my current VA lesson teach about the future?").type == QuestionType.COURSE


def test_greetings_and_job_listings_short_circuit():
    assert kind("hello").type == QuestionType.GREETING
    assert kind("Are there any jobs available?").type == QuestionType.CAREER


@pytest.mark.parametrize("message", [
    "What are its advantages?", "explain that", "another example", "How many types?", "ምሳሌ",
    "How does it help clients?",
])
def test_messages_that_point_back_are_follow_ups_with_history(message):
    assert kind(message, FREELANCING_HISTORY).type == QuestionType.FOLLOW_UP


@pytest.mark.parametrize("message", ["What are its advantages?", "Can you explain this?", "another example"])
def test_messages_that_point_back_without_history_are_ambiguous(message):
    assert kind(message).type == QuestionType.AMBIGUOUS


@pytest.mark.parametrize("message", [
    "What is the difference between freelancing and remote employment?",
    "Which tools do virtual assistants use?",
    "Tell me about this course",
    "Why does Python use indentation in code blocks?",
])
def test_standalone_questions_are_not_follow_ups(message):
    assert not refers_back(message)


def test_language_switch_without_topic_is_a_follow_up_but_with_topic_is_standalone():
    assert kind("Explain your previous answer in Amharic.", FREELANCING_HISTORY).type == QuestionType.FOLLOW_UP
    assert kind("Explain your previous answer in Amharic.").type == QuestionType.AMBIGUOUS
    assert kind("What is a virtual assistant in Amharic?").type != QuestionType.FOLLOW_UP


def test_query_helpers_remove_words_that_are_not_course_topics():
    assert strip_language_switch("What is a VA in Amharic?") == "What is a VA ?"
    assert "lesson" not in strip_course_meta("What did my current VA lesson teach about the future?").lower()


# --- routing through TutorService -------------------------------------------------------------

CORPUS = [{
    "id": "course:va--intro--freelancing", "scope": "course:va", "course": "VA", "lesson_id": "intro",
    "title": "VA Foundations", "section": "Freelancing Paths", "anchor": "#freelancing",
    "url": "/va.html#freelancing",
    "text": "Freelancing means you work independently for one or more clients and manage your own schedule.",
}]


class RecordingProvider:
    name = "stub"

    def __init__(self):
        self.calls = []

    def generate(self, question, passages, language, simple=False, history=None, *, confidence=0.0, **kwargs):
        self.calls.append({"question": question, "passages": passages, "history": history, **kwargs})
        return ChatResponse(status=ChatStatus.ANSWERED, language=language, answer="ok",
                            citations=[p.to_citation() for p in passages],
                            answer_source="cloud_general" if not passages else "cloud")


@pytest.fixture
def routed(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save(CORPUS)
    provider = RecordingProvider()
    return TutorService(store, provider, settings=Settings(enable_exact_cache=False)), provider


def ask(tutor, message, history=()):
    return tutor.answer(ChatRequest(message=message, scope="course:va", language="en", history=list(history)))


def test_unrelated_question_never_reaches_the_provider(routed):
    tutor, provider = routed
    res = ask(tutor, "What is photosynthesis?")
    assert res.status == ChatStatus.OUT_OF_SCOPE and res.question_type == "unrelated"
    assert provider.calls == []


def test_greeting_never_reaches_the_provider(routed):
    tutor, provider = routed
    assert ask(tutor, "hello").question_type == "greeting"
    assert provider.calls == []


def test_follow_up_is_grounded_in_the_previous_topic_and_keeps_the_current_question(routed):
    tutor, provider = routed
    res = ask(tutor, "What are its advantages?", FREELANCING_HISTORY)
    assert res.question_type == "follow_up" and res.status == ChatStatus.ANSWERED
    call = provider.calls[-1]
    assert call["question"] == "What are its advantages?"
    assert [p.section for p in call["passages"]] == ["Freelancing Paths"]
    assert call["history"]


def test_follow_up_answers_are_not_cached_across_conversations(tmp_path):
    from assistant.infrastructure.answer_cache import AnswerCache

    store = ChunkStore(tmp_path / "chunks.json")
    store.save(CORPUS)
    provider = RecordingProvider()
    settings = Settings(enable_exact_cache=True, ai_provider="cloud", gemini_model="test")
    tutor = TutorService(store, provider, cache=AnswerCache(settings), settings=settings)
    ask(tutor, "What are its advantages?", FREELANCING_HISTORY)
    ask(tutor, "What are its advantages?", FREELANCING_HISTORY)
    assert len(provider.calls) == 2


def test_ambiguous_question_asks_which_topic(routed):
    tutor, provider = routed
    res = ask(tutor, "What are its advantages?")
    assert res.status == ChatStatus.NEEDS_CLARIFICATION and res.question_type == "ambiguous"
    assert provider.calls == []
