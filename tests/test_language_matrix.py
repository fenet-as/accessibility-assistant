"""Milestone 2 language matrix: messages, status map, Telegram prefs."""

import pytest

from assistant.channels.telegram import LANGUAGE_SWITCHED, START_KEYBOARD, TelegramAdapter
from assistant.domain.language import (
    LANGUAGE_STATUS,
    SUPPORTED_LANGUAGES,
    UI_STRINGS,
    language_catalog,
    language_status,
)
from assistant.domain.messages import (
    ESCALATION_CREATED,
    FAREWELL_REPLY,
    GREETING_REPLY,
    NEEDS_CLARIFICATION,
    NOT_FOUND,
    OUT_OF_SCOPE,
    THANKS_REPLY,
    TRANSLATION_UNAVAILABLE,
    UNCLEAR_REFERENCE,
    detect_social_response,
)


MESSAGE_PACKS = (
    NOT_FOUND,
    OUT_OF_SCOPE,
    UNCLEAR_REFERENCE,
    ESCALATION_CREATED,
    NEEDS_CLARIFICATION,
    TRANSLATION_UNAVAILABLE,
    GREETING_REPLY,
    FAREWELL_REPLY,
    THANKS_REPLY,
)

REQUIRED_UI_KEYS = (
    "launcher", "placeholder", "loading", "send", "voice_aria", "listen",
    "offline_error", "experimental", "english_source", "welcome",
)


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_every_message_pack_covers_all_languages(code):
    for pack in MESSAGE_PACKS:
        assert code in pack and pack[code].strip()


@pytest.mark.parametrize("code", SUPPORTED_LANGUAGES)
def test_ui_strings_cover_required_keys(code):
    for key in REQUIRED_UI_KEYS:
        assert UI_STRINGS[code][key].strip()


def test_language_status_marks_only_en_am_verified():
    assert language_status("en") == language_status("am") == "verified"
    for code in ("ti", "om", "so", "ar"):
        assert LANGUAGE_STATUS[code] == "experimental"
    catalog = {row["code"]: row["status"] for row in language_catalog()}
    assert catalog["en"] == "verified" and catalog["ti"] == "experimental"


@pytest.mark.parametrize("text, language", [
    ("hello", "en"),
    ("ሰላም እንዴት ነህ", "am"),
    ("ከመይ ኣለኻ", "ti"),
    ("akkam", "om"),
    ("salaan", "so"),
    ("مرحبا", "ar"),
])
def test_greetings_reply_in_matched_language(text, language):
    response = detect_social_response(text, "auto")
    assert response is not None
    assert response.language == language


def test_telegram_keyboard_lists_six_languages():
    codes = []
    for row in START_KEYBOARD["inline_keyboard"]:
        for button in row:
            data = button.get("callback_data", "")
            if data.startswith("lang_"):
                codes.append(data.split("_", 1)[1])
    assert codes == list(SUPPORTED_LANGUAGES)
    assert set(LANGUAGE_SWITCHED) == set(SUPPORTED_LANGUAGES)


@pytest.mark.anyio
async def test_telegram_language_persists_in_sqlite(container, monkeypatch):
    adapter = TelegramAdapter(container, token="test-token")
    chat_id = 424242

    async def _noop_send(chat_id, text, reply_markup=None):
        return True

    monkeypatch.setattr(adapter, "send_message", _noop_send)
    result = await adapter._set_language(chat_id, "am")
    assert result["action"] == "set_language"
    assert adapter._get_language(chat_id) == "am"
    # Fresh adapter reads from SQLite, not the in-memory cache.
    again = TelegramAdapter(container, token="test-token")
    assert again._get_language(chat_id) == "am"
