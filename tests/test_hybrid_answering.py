"""Phase 3: general-knowledge answering, genuine citations, and channel session history."""

from __future__ import annotations

from assistant.config import Settings
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers.answer_mode import COURSE, GENERAL, GENERAL_HEADING
from assistant.infrastructure.providers.gemini import build_prompt, build_system_instruction, cited_passages
from assistant.infrastructure.session_history import SessionHistoryStore
from assistant.services.tutor import TutorService


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

    def generate(
        self, question, passages, language, simple=False, history=None, *, confidence=0.0,
        answer_mode=COURSE, scope_confirmed=True,
    ):
        self.calls.append({
            "question": question,
            "passages": list(passages),
            "history": list(history or []),
            "answer_mode": answer_mode,
            "scope_confirmed": scope_confirmed,
        })
        if answer_mode == GENERAL or not passages:
            return ChatResponse(
                status=ChatStatus.ANSWERED,
                language=language,
                answer="General knowledge answer about building a portfolio.",
                citations=[],
                provider=self.name,
                answer_source="cloud_general",
            )
        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=f"Course answer citing {passages[0].section}.",
            citations=[p.to_citation() for p in passages],
            provider=self.name,
            answer_source="cloud",
        )


def make_tutor(tmp_path, provider=None, history=None):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save(CORPUS)
    provider = provider or RecordingProvider()
    tutor = TutorService(
        store,
        provider,
        settings=Settings(enable_exact_cache=False),
        session_history=history or SessionHistoryStore(),
    )
    return tutor, provider


def test_general_question_without_course_evidence_uses_general_mode(tmp_path):
    tutor, provider = make_tutor(tmp_path)
    res = tutor.answer(ChatRequest(
        message="How do I create a professional portfolio?",
        scope="course:va",
        language="en",
        session="s1",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.question_type == "career"
    assert res.answer_source == "cloud_general"
    assert res.citations == []
    assert provider.calls[-1]["answer_mode"] == GENERAL
    assert provider.calls[-1]["passages"] == []


def test_course_question_still_sends_passages(tmp_path):
    tutor, provider = make_tutor(tmp_path)
    res = tutor.answer(ChatRequest(message="What is freelancing?", scope="course:va", language="en"))
    assert res.status == ChatStatus.ANSWERED
    assert res.question_type == "course"
    assert provider.calls[-1]["answer_mode"] == COURSE
    assert [p.section for p in provider.calls[-1]["passages"]] == ["Freelancing Paths"]
    assert res.citations


def test_general_answers_do_not_get_fake_course_citations():
    passage = Passage(
        id="p1", course="VA", title="VA", section="Freelancing Paths",
        anchor="#f", url="/f", text="Freelancing means independent client work.",
    )
    assert cited_passages("A portfolio shows your best work samples.", [passage]) == []
    assert cited_passages("As covered in Freelancing Paths, freelancers invoice clients.", [passage])


def test_course_prompt_allows_labeled_general_knowledge():
    system = build_system_instruction("en", False, answer_mode=COURSE)
    assert GENERAL_HEADING in system
    assert "GENERAL EDUCATIONAL KNOWLEDGE" not in system
    general = build_system_instruction("en", False, answer_mode=GENERAL)
    assert "Do NOT invent course citations" in general
    prompt = build_prompt("What is freelancing?", [], "en", answer_mode=GENERAL)
    assert "No course passages" in prompt


def test_session_history_lets_telegram_style_follow_ups_work(tmp_path):
    history = SessionHistoryStore()
    tutor, provider = make_tutor(tmp_path, history=history)

    first = tutor.answer(ChatRequest(
        session="tg-42", message="What is freelancing?", scope="course:va", language="en",
    ))
    assert first.status == ChatStatus.ANSWERED
    assert history.get("tg-42")

    follow = tutor.answer(ChatRequest(
        session="tg-42", message="What are its advantages?", scope="course:va", language="en",
        history=[],  # channel did not send history
    ))
    assert follow.question_type == "follow_up"
    assert follow.status == ChatStatus.ANSWERED
    assert provider.calls[-1]["history"]
    assert provider.calls[-1]["question"] == "What are its advantages?"


def test_follow_up_without_evidence_still_uses_general_mode_with_context(tmp_path):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save([])  # empty knowledge base
    provider = RecordingProvider()
    tutor = TutorService(store, provider, settings=Settings(enable_exact_cache=False))
    res = tutor.answer(ChatRequest(
        message="What are its advantages?",
        language="en",
        scope="course:va",
        history=[
            ConversationTurn(role="user", content="What is freelancing?"),
            ConversationTurn(role="assistant", content="Freelancing is independent client work."),
        ],
    ))
    assert res.question_type == "follow_up"
    assert provider.calls[-1]["answer_mode"] == GENERAL
    assert provider.calls[-1]["history"]
