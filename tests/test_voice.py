"""Tests for Addis AI voice endpoints."""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from assistant.api.app import create_app
from assistant.container import build_container


def test_voice_status_endpoint(client):
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "addis_ai"
    assert "am" in data["tts_languages"]
    assert "ti" in data["tts_languages"]
    assert "om" in data["tts_languages"]


def test_voice_speak_unconfigured(monkeypatch):
    container = build_container()
    container.addis_ai.api_key = ""
    app = create_app(container)
    c = TestClient(app)

    res = c.get("/api/voice/speak?text=ሰላም&language=am")
    assert res.status_code == 503


def test_voice_speak_mocked_success(monkeypatch):
    container = build_container()
    container.addis_ai.api_key = "test-key"
    monkeypatch.setattr(container.addis_ai, "synthesize", lambda text, language: b"ID3\x03fake-mp3-audio-bytes")
    app = create_app(container)
    c = TestClient(app)

    res = c.get("/api/voice/speak?text=ሰላም&language=am")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert res.content.startswith(b"ID3")


def test_voice_transcribe_unconfigured(monkeypatch):
    container = build_container()
    container.addis_ai.api_key = ""
    app = create_app(container)
    c = TestClient(app)

    res = c.post(
        "/api/voice/transcribe?language=am",
        content=b"fake-audio-bytes",
        headers={"Content-Type": "audio/webm"},
    )
    assert res.status_code == 503


def test_voice_transcribe_mocked_success(monkeypatch):
    container = build_container()
    container.addis_ai.api_key = "test-key"
    monkeypatch.setattr(
        container.addis_ai,
        "transcribe",
        lambda audio_bytes, language, filename, content_type: "ሰላም እንኳን ደህና መጡ",
    )
    app = create_app(container)
    c = TestClient(app)

    res = c.post(
        "/api/voice/transcribe?language=am",
        content=b"fake-audio-bytes",
        headers={"Content-Type": "audio/webm"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "ሰላም እንኳን ደህና መጡ"
    assert data["language"] == "am"


def test_widget_voice_endpoints_integrated(client):
    res = client.get("/widget/assistant.js")
    assert res.status_code == 200
    source = res.text
    assert "/voice/speak" in source
    assert "/voice/transcribe" in source
    assert "MediaRecorder" in source
    assert "speechSynthesis" in source
    assert "SpeechRecognition" in source
