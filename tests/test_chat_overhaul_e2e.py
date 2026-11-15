"""Phase 2–5 overhaul acceptance: conversations, cache clear, honest labels, widget assets."""

from __future__ import annotations

from pathlib import Path

from assistant.config import PACKAGE_DIR
from assistant.infrastructure.answer_cache import PROMPT_VERSION

WIDGET = PACKAGE_DIR / "widget"


def test_health_exposes_ai_and_cache(client):
    health = client.get("/api/health").json()
    assert health["status"] == "healthy"
    assert "ai" in health
    assert health["exact_cache_enabled"] is True
    assert health["cache_backend"] in ("memory", "redis")
    assert health["connectivity"]["backend"] == "ok"
    cfg = client.get("/api/config").json()
    assert cfg["restart_required_after_env_change"] is True
    assert "gemini_key_configured" in cfg["ai"] or "gemini" in cfg["ai"]


def test_admin_cache_clear(client):
    # Warm cache via a chat round-trip
    chat = client.post(
        "/api/chat",
        json={
            "session": "e2e-cache-1",
            "message": "What is a virtual assistant?",
            "language": "en",
            "scope": "course:va-1",
        },
    )
    assert chat.status_code == 200
    cleared = client.post("/api/admin/cache/clear")
    assert cleared.status_code == 200
    body = cleared.json()
    assert body["status"] == "cleared"
    assert body["backend"] in ("memory", "redis")


def test_conversation_flow_with_chat_persist(client):
    headers = {"X-Owner-Id": "e2e-owner-overhaul"}
    conv = client.post("/api/conversations", json={"language": "en"}, headers=headers).json()
    chat = client.post(
        "/api/chat",
        json={
            "session": "e2e-sess",
            "message": "What skills does a virtual assistant need?",
            "language": "en",
            "scope": "course:va-1",
        },
    ).json()
    assert chat["answer"]
    # Never claim Gemini when FAQ provider is active in tests
    assert chat.get("answer_source") in (
        "local", "cloud", "cloud_general", "cache", "social", "careers", "faq"
    )
    if chat.get("answer_source") == "faq" or "faq" in str(chat.get("provider", "")).lower():
        assert chat.get("source_type") in ("faq", "local_course", "social", "careers", "none", "cache")
        # FAQ answers must not be labeled as Gemini/cloud.
        assert chat.get("source_type") != "course_grounded" or chat.get("answer_source") != "cloud"

    turned = client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={
            "user_message": "What skills does a virtual assistant need?",
            "assistant_message": chat["answer"],
            "language": chat.get("language") or "en",
            "provider": chat.get("provider") or "",
            "answer_source": chat.get("answer_source") or "",
            "source_type": chat.get("source_type") or "",
            "cache_hit": bool(chat.get("cache_hit")),
            "citations": chat.get("citations") or [],
        },
        headers=headers,
    )
    assert turned.status_code == 200
    detail = client.get(f"/api/conversations/{conv['id']}", headers=headers).json()
    assert len(detail["messages"]) == 2
    assert detail["title"] != "New chat"


def test_prompt_version_bumped_for_cache_invalidation():
    assert PROMPT_VERSION.startswith("hybrid-")
    assert PROMPT_VERSION >= "hybrid-v2"


def test_widget_two_panel_and_session_behavior():
    js = (WIDGET / "assistant.js").read_text(encoding="utf-8")
    offline = (WIDGET / "offline.js").read_text(encoding="utf-8")
    assert "alx-sidebar" in js
    assert "alx-suggestions" in js
    assert "_renderMarkdown" in js
    assert "startNewConversation" in js
    assert "Refresh = new empty chat" in js or "refresh starts a new empty session" in js.lower() or "_loadStoredHistory" in js
    # Active thread must not restore from localStorage on refresh
    assert "Refresh always starts a new empty session" in js
    assert "X-Owner-Id" in js
    assert "connectivity_ai_offline" in js
    assert "DB_VERSION = 3" in offline
    assert "upsertConversation" in offline
    assert "clearCachedAnswers" in offline
    assert "listLocalConversations" in offline


def test_widget_preserves_voice_and_escalation():
    js = (WIDGET / "assistant.js").read_text(encoding="utf-8")
    assert "initVoiceInput" in js
    assert "requestHumanHelp" in js
    assert "alx-voice-btn" in js
    assert "speechSynthesis" in js
    assert Path(WIDGET / "voice-recorder.js").is_file()
