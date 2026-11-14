"""Milestone 2: six-language configuration, detection, RTL/Ethiopic UI, offline answers."""

import pytest

from assistant.domain.language import (
    LANGUAGES,
    SUPPORTED_LANGUAGES,
    UI_STRINGS,
    detect_language,
    detect_language_with_confidence,
    language_catalog,
)
from assistant.domain.messages import NOT_FOUND, TRANSLATION_UNAVAILABLE, localized
from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.providers import OfflineFAQProvider
from assistant.services.tutor import TutorService


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_every_supported_language_has_config_and_ui_pack(code):
    spec = LANGUAGES[code]
    assert spec.name_en and spec.name_native and spec.script in {"latin", "ethiopic", "arabic"}
    assert spec.direction in {"ltr", "rtl"}
    assert spec.speech_recognition and spec.speech_synthesis
    for key in ("launcher", "placeholder", "loading", "send", "voice_aria", "listen", "offline_error"):
        assert UI_STRINGS[code][key]


def test_arabic_is_rtl_and_ethiopic_languages_are_ltr():
    assert LANGUAGES["ar"].direction == "rtl" and LANGUAGES["ar"].script == "arabic"
    assert LANGUAGES["am"].script == LANGUAGES["ti"].script == "ethiopic"
    assert LANGUAGES["am"].direction == LANGUAGES["ti"].direction == "ltr"
    assert {LANGUAGES[c].script for c in ("en", "om", "so")} == {"latin"}


def test_manual_override_always_wins_with_full_confidence():
    guess = detect_language_with_confidence("How can AI help?", "ar")
    assert guess.code == "ar" and guess.confidence == 1.0 and guess.overridden is True


@pytest.mark.parametrize("text, expected", [
    ("What is shaping the future of VA work?", "en"),
    ("ቨርቹዋል ረዳት ምንድን ነው?", "am"),
    ("እንታይ እዩ ስራሕ ሓጋዚ ቨርቹዋል?", "ti"),
    ("Maal ta'a gargaarsa virtualii?", "om"),
    ("Maxay tahay caawimaadda virtual?", "so"),
    ("ما هو المساعد الافتراضي؟", "ar"),
])
def test_detection_uses_markers_not_only_script(text, expected):
    guess = detect_language_with_confidence(text, "auto")
    assert guess.code == expected
    assert guess.confidence >= 0.35
    assert guess.overridden is False


def test_shared_scripts_are_disambiguated_by_markers():
    am = detect_language("ቨርቹዋል ረዳት ሥራ ምን ይመስላል?", "auto")
    ti = detect_language("እንታይ እዩ ስራሕ ሓጋዚ ዘሎ?", "auto")
    om = detect_language("Akkam gargaarsa barnootaa jira?", "auto")
    so = detect_language("Sidee bay shaqo caawimaad u shaqeysaa?", "auto")
    assert am == "am" and ti == "ti"
    assert om == "om" and so == "so"


def test_languages_api_exposes_catalog(client):
    res = client.get("/api/languages")
    assert res.status_code == 200
    body = res.json()
    assert body["supported"] == list(SUPPORTED_LANGUAGES)
    codes = [lang["code"] for lang in body["languages"]]
    assert codes == list(SUPPORTED_LANGUAGES)
    arabic = next(lang for lang in body["languages"] if lang["code"] == "ar")
    assert arabic["direction"] == "rtl" and arabic["ui"]["send"]
    assert client.get("/api/health").json()["languages"] == list(SUPPORTED_LANGUAGES)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_chat_honours_selected_language_for_answers_and_system_copy(client, language):
    answered = client.post("/api/chat", json={
        "session": "lang-test",
        "message": "How can AI help virtual assistants?",
        "language": language,
        "scope": "course:va-1",
    }).json()
    assert answered["status"] == "answered"
    assert answered["language"] == language
    assert answered["language_overridden"] is True
    assert answered["language_confidence"] == 1.0
    assert answered["citations"]

    rejected = client.post("/api/chat", json={
        "session": "lang-test",
        "message": "What is the capital of France?",
        "language": language,
        "scope": "course:va-1",
    }).json()
    assert rejected["status"] == "not_found"
    assert rejected["answer"] == localized(NOT_FOUND, language)


def test_offline_provider_never_invents_missing_translations(tmp_path, container):
    store = ChunkStore(tmp_path / "chunks.json")
    store.save([{
        "id": "demo--one--intro", "scope": "course:demo", "course": "Demo", "lesson_id": "one",
        "title": "Demo", "section": "Intro", "anchor": "#intro", "url": "/demo#intro",
        "text": "Photosynthesis converts sunlight into sugar for the plant.",
        "translations": {},
    }])
    tutor = TutorService(store, OfflineFAQProvider(container.settings.faq_translations_path))
    res = tutor.answer(ChatRequest(
        message="How does photosynthesis convert sunlight into sugar?",
        language="ar",
        scope="course:demo",
    ))
    assert res.status == ChatStatus.ANSWERED
    assert res.translation_fallback is True
    assert TRANSLATION_UNAVAILABLE["ar"].split(":")[0] in res.answer
    assert "Photosynthesis converts sunlight" in res.answer
    assert [c.section for c in res.citations] == ["Intro"]


def test_english_and_amharic_grounding_still_work(client):
    en = client.post("/api/chat", json={
        "message": "What is shaping the future of VA work?", "language": "en", "scope": "course:va-1",
    }).json()
    am = client.post("/api/chat", json={
        "message": "ሰው ሰራሽ አስተዋይነት ቨርቹዋል ረዳቶችን እንዴት ይረዳል?", "language": "am", "scope": "course:va-1",
    }).json()
    assert en["status"] == "answered" and en["language"] == "en"
    assert any("Shaping the Future" in c["section"] for c in en["citations"])
    assert am["status"] == "answered" and am["language"] == "am"
    assert any("Artificial Intelligence" in c["section"] for c in am["citations"])
    assert am["translation_fallback"] is False


def test_widget_supports_six_languages_rtl_ethiopic_and_voice_fallback(client):
    source = client.get("/widget/assistant.js").text
    for code in SUPPORTED_LANGUAGES:
        assert f"'{code}'" in source or f'"{code}"' in source
    assert 'dir="rtl"' in source or "direction === 'rtl'" in source or 'meta.dir' in source
    assert "Noto Sans Ethiopic" in source and "Noto Sans Arabic" in source
    assert 'id="alx-lang-select"' in source
    assert "speechSynthesis" in source and "SpeechRecognition" in source
    assert "speak_unsupported" in source and "voice_unsupported" in source
    assert "localStorage" in source
    catalog = language_catalog()
    assert len(catalog) == 6
