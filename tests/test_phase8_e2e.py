"""Phase 8 end-to-end acceptance matrix.

Default runs use a stubbed / FAQ provider so the free-tier Gemini quota is never spent.
Set RUN_LIVE_GEMINI=1 (and GEMINI_API_KEY) for the small live smoke at the bottom.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from assistant.config import PACKAGE_DIR, Settings
from assistant.domain.language import SUPPORTED_LANGUAGES
from assistant.domain.models import ChatRequest, ChatResponse, ChatStatus, ConversationTurn
from assistant.domain.source_meta import (
    CACHE,
    CAREERS,
    CONNECTIVITY_OFFLINE,
    CONNECTIVITY_ONLINE,
    COURSE_GROUNDED,
    FAQ,
    GENERAL_KNOWLEDGE,
    SOCIAL,
)
from assistant.infrastructure.answer_cache import AnswerCache
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers.answer_mode import COURSE, GENERAL
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider
from assistant.infrastructure.session_history import SessionHistoryStore
from assistant.infrastructure.usage import UsageTracker
from assistant.services.offline_pack import build_course_pack
from assistant.services.tutor import TutorService

# --- Acceptance questions (English) → expected citation section substring(s) ---
ACCEPTANCE_COURSE = [
    ("What is freelancing?", ("Freelancing and Employment Paths",)),
    ("Where do virtual assistants work?", ("Where Do Virtual Assistants Work?",)),
    ("What is a virtual assistant?", ("Introduction & Overview", "What is a Virtual Assistant")),
    ("What skills does a virtual assistant need?", ("Skills Clients Value",)),
    (
        "What is the difference between freelancing and remote employment?",
        ("Freelancing and Employment Paths",),
    ),
    ("How can I become a virtual assistant?", ("Getting Started as a Virtual Assistant",)),
    (
        "What are the responsibilities of a virtual assistant?",
        ("Common Virtual Assistant Responsibilities",),
    ),
    (
        "What did my current VA lesson teach about the future of the industry?",
        ("What is Shaping the Future", "So, is the Future of VA Promising", "Future of VA"),
    ),
]

# Phrases that match GREETING_PATTERNS for each language.
GREETINGS = {
    "en": "hello",
    "am": "ሰላም እንዴት ነህ",
    "ti": "ከመይ ኣለኻ",
    "om": "akkam",
    "so": "salaan",
    "ar": "مرحبا",
}


class StubProvider:
    """Deterministic online provider: course mode cites passages; general never invents citations."""

    name = "stub_gemini"

    def __init__(self):
        self.calls = []

    def generate(
        self,
        question,
        passages,
        language,
        simple=False,
        history=None,
        *,
        confidence=0.0,
        answer_mode=COURSE,
        scope_confirmed=True,
    ):
        self.calls.append({
            "question": question,
            "passages": list(passages),
            "history": list(history or []),
            "answer_mode": answer_mode,
            "language": language,
        })
        if answer_mode == GENERAL or not passages:
            # Mirror Gemini: unconfirmed non-English off-topic asks can be declined.
            if not scope_confirmed:
                return ChatResponse(
                    status=ChatStatus.OUT_OF_SCOPE,
                    language=language,
                    answer="OUT_OF_SCOPE",
                    citations=[],
                    provider=self.name,
                    answer_source="none",
                )
            return ChatResponse(
                status=ChatStatus.ANSWERED,
                language=language,
                answer="Stub general-knowledge answer with no course citations.",
                citations=[],
                provider=self.name,
                answer_source="cloud_general",
            )
        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=f"Stub course answer grounded in {passages[0].section}.",
            citations=[p.to_citation() for p in passages],
            provider=self.name,
            answer_source="cloud",
        )


def _tutor_with_stub(container, provider=None, *, enable_cache=False):
    settings = replace(container.settings, enable_exact_cache=enable_cache)
    provider = provider or StubProvider()
    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        provider,
        settings.relevance_threshold,
        cache=AnswerCache(settings) if enable_cache else None,
        usage=UsageTracker(),
        settings=settings,
        session_history=SessionHistoryStore(),
    )
    return tutor, provider


# ---------------------------------------------------------------------------
# Acceptance matrix (stubbed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("question, expected_sections", ACCEPTANCE_COURSE)
def test_acceptance_course_questions_cite_expected_sections(container, question, expected_sections):
    tutor, provider = _tutor_with_stub(container)
    res = tutor.answer(ChatRequest(message=question, language="en", scope="course:va-1"))
    assert res.status == ChatStatus.ANSWERED
    assert res.connectivity == CONNECTIVITY_ONLINE
    assert res.course_id == "course:va-1"
    assert res.citations, f"expected course citations for: {question}"
    assert any(
        any(exp in c.section for exp in expected_sections) for c in res.citations
    ), f"got {[c.section for c in res.citations]} for {question!r}"
    # Citations must come from passages the stub actually received.
    cited_sections = {c.section for c in res.citations}
    passed_sections = {p.section for p in provider.calls[-1]["passages"]}
    assert cited_sections <= passed_sections
    assert res.source_type in (COURSE_GROUNDED, FAQ, CACHE)
    assert provider.calls[-1]["answer_mode"] == COURSE


def test_acceptance_follow_up_uses_conversation_context(container):
    tutor, provider = _tutor_with_stub(container)
    first = tutor.answer(ChatRequest(
        session="e2e-follow",
        message="What is freelancing?",
        language="en",
        scope="course:va-1",
    ))
    assert first.status == ChatStatus.ANSWERED

    follow = tutor.answer(ChatRequest(
        session="e2e-follow",
        message="What are its advantages?",
        language="en",
        scope="course:va-1",
        history=[],  # Telegram/SMS style — server session history fills context
    ))
    assert follow.question_type == "follow_up"
    assert follow.status == ChatStatus.ANSWERED
    assert provider.calls[-1]["history"]
    assert provider.calls[-1]["question"] == "What are its advantages?"


def test_acceptance_language_switch_follow_up(container):
    tutor, provider = _tutor_with_stub(container)
    tutor.answer(ChatRequest(
        session="e2e-am",
        message="What is freelancing?",
        language="en",
        scope="course:va-1",
    ))
    follow = tutor.answer(ChatRequest(
        session="e2e-am",
        message="Explain your previous answer in Amharic",
        language="auto",
        scope="course:va-1",
    ))
    assert follow.status == ChatStatus.ANSWERED
    assert follow.language == "am"
    assert provider.calls[-1]["language"] == "am"


def test_general_question_gets_general_answer_without_fake_citations(container):
    tutor, provider = _tutor_with_stub(container)
    res = tutor.answer(ChatRequest(
        message="How do I create a professional portfolio for freelancing clients?",
        language="en",
        scope="course:va-1",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.answer_source == "cloud_general"
    assert res.source_type == GENERAL_KNOWLEDGE
    assert res.citations == []
    assert provider.calls[-1]["answer_mode"] == GENERAL
    assert provider.calls[-1]["passages"] == []


# ---------------------------------------------------------------------------
# Six-language matrix (stubbed / social / scope policy)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_greeting_matrix_all_languages(container, code):
    tutor, _ = _tutor_with_stub(container)
    res = tutor.answer(ChatRequest(
        message=GREETINGS[code],
        language=code,  # force reply language (detector can disagree on short Latin greetings)
        scope="course:va-1",
        session=f"greet-{code}",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.language == code
    assert res.source_type == SOCIAL
    assert res.course_id == "course:va-1"
    assert res.connectivity == CONNECTIVITY_ONLINE


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_out_of_scope_matrix_all_languages(container, code):
    """English off-topic text + language override → localized scope-policy reply, no AI call."""
    tutor, provider = _tutor_with_stub(container)
    res = tutor.answer(ChatRequest(
        message="How do I bake a chocolate cake?",
        language=code,
        scope="course:va-1",
        session=f"oos-{code}",
    ))
    assert res.status == ChatStatus.OUT_OF_SCOPE
    assert res.language == code
    assert res.citations == []
    assert provider.calls == []  # classifier declines before the generative provider


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_course_question_language_override_matrix(container, code):
    """Course retrieval still works when the learner forces each UI language."""
    tutor, provider = _tutor_with_stub(container)
    res = tutor.answer(ChatRequest(
        message="What is freelancing?",
        language=code,
        scope="course:va-1",
        session=f"course-lang-{code}",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.language == code
    assert res.citations
    assert provider.calls[-1]["language"] == code


# ---------------------------------------------------------------------------
# Cache, Gemini failure, offline pack
# ---------------------------------------------------------------------------


def test_cached_answers_are_identified(container):
    tutor, provider = _tutor_with_stub(container, enable_cache=True)
    msg = "What is shaping the future of VA work?"
    first = tutor.answer(ChatRequest(message=msg, language="en", scope="course:va-1", session="cache-a"))
    second = tutor.answer(ChatRequest(message=msg, language="en", scope="course:va-1", session="cache-b"))
    assert first.status == second.status == ChatStatus.ANSWERED
    assert second.cache_hit is True
    assert second.answer_source == "cache"
    assert second.source_type == CACHE
    assert len(provider.calls) == 1


def test_failed_gemini_produces_honest_faq_fallback(container, monkeypatch):
    faq = OfflineFAQProvider(container.settings.faq_translations_path)
    provider = GeminiProvider("fake-key", "gemini-2.5-flash", faq, timeout_seconds=0.05)
    provider.client = MagicMock()

    def _boom(*a, **k):
        raise RuntimeError("simulated Gemini outage")

    monkeypatch.setattr(provider, "_call_gemini", _boom)
    settings = replace(container.settings, enable_exact_cache=False, ai_provider="cloud")
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
    assert res.fallback_reason  # honest reason, not silent cloud label
    assert res.answer_source == "faq"
    assert res.source_type == FAQ
    assert res.provider == "offline_faq"


def test_offline_pack_never_claims_cloud_ai(container):
    pack = build_course_pack(
        container.courses.store,
        "course:va-1",
        kb_version=container.tutor.kb_version,
        low_confidence=container.settings.relevance_threshold,
    )
    assert pack["offline_capabilities"]["cloud_ai"] is False
    assert pack["offline_capabilities"]["local_retrieval"] is True
    assert "offline_general_unavailable" in pack["messages"]

    # JS offline runtime must also refuse to claim Gemini and answer from pack data.
    if shutil.which("node") is None:
        pytest.skip("node required for offline JS smoke")
    script = Path(__file__).resolve().parent.parent / "evaluation" / "js_offline_smoke.js"
    pack_path = Path(container.settings.chunks_path).parent / "_phase8_pack.json"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(script), str(pack_path)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["ok"] is True
        assert payload["unknown_status"] == "not_found"
    finally:
        pack_path.unlink(missing_ok=True)


def test_api_chat_returns_phase7_metadata(client):
    res = client.post("/api/chat", json={
        "session": "e2e-meta",
        "message": "What is a virtual assistant?",
        "language": "en",
        "scope": "course:va-1",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "answered"
    assert data["course_id"] == "course:va-1"
    assert data["connectivity"] == CONNECTIVITY_ONLINE
    assert data["source_type"] in (FAQ, COURSE_GROUNDED, CACHE)
    assert data.get("answer_source")  # compatibility


def test_api_careers_path_labels_source_type(client):
    res = client.post("/api/chat", json={
        "session": "e2e-jobs",
        "message": "What VA jobs are available?",
        "language": "en",
        "scope": "course:va-1",
    })
    assert res.status_code == 200
    data = res.json()
    if data["status"] == "answered" and data.get("provider") == "careers":
        assert data["source_type"] == CAREERS


# ---------------------------------------------------------------------------
# Live Gemini smoke (opt-in, budgeted)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_gemini_smoke_budgeted(container):
    """At most two live Gemini calls. Skip unless explicitly enabled."""
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    if os.environ.get("RUN_LIVE_GEMINI", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_LIVE_GEMINI=1 to hit the live Gemini API (free tier is limited)")

    from assistant.infrastructure.providers import build_provider

    settings = replace(
        container.settings,
        ai_provider="cloud",
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        enable_exact_cache=True,  # second identical ask should hit cache, not Gemini
    )
    usage = UsageTracker()
    tutor = TutorService(
        ChunkStore(settings.chunks_path),
        build_provider(settings, usage=usage),
        settings.relevance_threshold,
        cache=AnswerCache(settings),
        usage=usage,
        settings=settings,
    )

    # Call 1: course-grounded
    course = tutor.answer(ChatRequest(
        message="What is a virtual assistant?",
        language="en",
        scope="course:va-1",
        session="live-1",
    ))
    assert course.status in (ChatStatus.ANSWERED, ChatStatus.NOT_FOUND, ChatStatus.OUT_OF_SCOPE)
    if course.status == ChatStatus.ANSWERED and course.answer_source == "cloud":
        assert course.citations  # grounded cloud answers should name a real section
        for citation in course.citations:
            assert citation.section.strip()

    # Call 2: general knowledge (no fake citations)
    general = tutor.answer(ChatRequest(
        message="How do I create a professional portfolio?",
        language="en",
        scope="course:va-1",
        session="live-2",
    ))
    assert general.status in (ChatStatus.ANSWERED, ChatStatus.NOT_FOUND, ChatStatus.OUT_OF_SCOPE)
    if general.status == ChatStatus.ANSWERED and general.answer_source == "cloud_general":
        assert general.citations == []
        assert general.source_type == GENERAL_KNOWLEDGE

    # Cache replay of call 1 — must not spend another Gemini request when cacheable.
    replay = tutor.answer(ChatRequest(
        message="What is a virtual assistant?",
        language="en",
        scope="course:va-1",
        session="live-3",
    ))
    if course.status == ChatStatus.ANSWERED and course.answer_source in ("cloud", "faq", "cache"):
        # If the first answer was cacheable, replay should be a hit.
        if replay.cache_hit:
            assert replay.source_type == CACHE
