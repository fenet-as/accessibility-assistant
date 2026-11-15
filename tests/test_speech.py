"""Whisper STT validation, status honesty, threadpool, timings, typed errors."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from assistant.infrastructure.speech import (
    SttTimeoutError,
    TranscribeResult,
    resolve_whisper_language,
    stt_status,
    validate_audio_upload,
    whisper_available,
)


def test_stt_status_requires_sdk_and_key(monkeypatch):
    settings = MagicMock(openai_api_key="sk-test", whisper_api_key="", whisper_model="whisper-1")
    monkeypatch.setattr("assistant.infrastructure.speech.openai_sdk_available", lambda: False)
    status = stt_status(settings)
    assert status["server_stt"] is False
    assert status["key_configured"] is True
    assert status["sdk_installed"] is False

    monkeypatch.setattr("assistant.infrastructure.speech.openai_sdk_available", lambda: True)
    assert stt_status(settings)["server_stt"] is True
    assert whisper_available("sk-test") is True


def test_ti_and_om_use_auto_detect_with_warning():
    lang, warning = resolve_whisper_language("ti")
    assert lang is None and warning and "ti" in warning
    lang, warning = resolve_whisper_language("om")
    assert lang is None and warning and "om" in warning
    lang, warning = resolve_whisper_language("am")
    assert lang == "am" and warning is None


def test_validate_audio_rejects_bad_mime_and_size():
    assert validate_audio_upload(
        payload=b"x", filename="a.webm", mime_type="audio/webm", max_bytes=10, max_seconds=60
    ) is None
    assert "Empty" in (validate_audio_upload(
        payload=b"", filename="a.webm", mime_type="audio/webm", max_bytes=10, max_seconds=60
    ) or "")
    assert "too large" in (validate_audio_upload(
        payload=b"x" * 20, filename="a.webm", mime_type="audio/webm", max_bytes=10, max_seconds=60
    ) or "").lower()
    assert "Unsupported" in (validate_audio_upload(
        payload=b"abcd", filename="a.exe", mime_type="application/octet-stream", max_bytes=100, max_seconds=60
    ) or "")


def _fake_timed(*a, **k):
    hint = k.get("language_hint", "auto")
    if hint in ("ti", "om"):
        return TranscribeResult(
            text="hello",
            language_used="auto",
            language_warning=f"Whisper has no dedicated model for '{hint}'",
            timings={"prepare_ms": 0.1, "whisper_ms": 12.0, "total_ms": 12.1},
        )
    return TranscribeResult(
        text="hello",
        language_used="en",
        language_warning=None,
        timings={"prepare_ms": 0.1, "whisper_ms": 10.0, "total_ms": 10.1},
    )


def test_transcribe_endpoint_validation(client, monkeypatch):
    monkeypatch.setattr("assistant.api.routers.speech.whisper_available", lambda key: True)
    monkeypatch.setattr("assistant.api.routers.speech.transcribe_audio_timed", _fake_timed)

    res = client.post(
        "/api/transcribe",
        files={"audio": ("speech.webm", b"", "audio/webm")},
        data={"language": "en"},
    )
    assert res.status_code == 400

    res = client.post(
        "/api/transcribe",
        files={"audio": ("speech.webm", b"fake-audio-bytes", "audio/webm")},
        data={"language": "ti"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "hello"
    assert "language_warning" in body
    assert "timings" in body
    assert "whisper_ms" in body["timings"]
    assert "Server-Timing" in res.headers


def test_transcribe_endpoint_rejects_when_unavailable(client, monkeypatch):
    monkeypatch.setattr("assistant.api.routers.speech.whisper_available", lambda key: False)
    res = client.post(
        "/api/transcribe",
        files={"audio": ("speech.webm", b"abc", "audio/webm")},
        data={"language": "en"},
    )
    assert res.status_code == 503


def test_transcribe_maps_timeout_error(client, monkeypatch):
    monkeypatch.setattr("assistant.api.routers.speech.whisper_available", lambda key: True)

    def boom(*a, **k):
        raise SttTimeoutError("Transcription timed out")

    monkeypatch.setattr("assistant.api.routers.speech.transcribe_audio_timed", boom)
    res = client.post(
        "/api/transcribe",
        files={"audio": ("speech.webm", b"fake-audio-bytes", "audio/webm")},
        data={"language": "en"},
    )
    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()


def test_transcribe_does_not_block_event_loop(client, monkeypatch):
    """A slow Whisper call must not prevent concurrent /health responses."""
    monkeypatch.setattr("assistant.api.routers.speech.whisper_available", lambda key: True)

    def slow(*a, **k):
        time.sleep(0.35)
        return TranscribeResult(
            text="slow-ok",
            language_used="en",
            timings={"whisper_ms": 350.0, "total_ms": 350.0},
        )

    monkeypatch.setattr("assistant.api.routers.speech.transcribe_audio_timed", slow)

    import concurrent.futures

    def do_transcribe():
        return client.post(
            "/api/transcribe",
            files={"audio": ("speech.webm", b"fake-audio-bytes", "audio/webm")},
            data={"language": "en"},
        )

    def do_health():
        # Give the transcribe a head start so it is in-flight.
        time.sleep(0.05)
        started = time.perf_counter()
        res = client.get("/api/health")
        elapsed = time.perf_counter() - started
        return res, elapsed

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_tr = pool.submit(do_transcribe)
        f_h = pool.submit(do_health)
        tr = f_tr.result(timeout=5)
        health, health_elapsed = f_h.result(timeout=5)

    assert tr.status_code == 200
    assert health.status_code == 200
    # Health must return well before the 350ms Whisper sleep finishes blocking a sync endpoint.
    assert health_elapsed < 0.3, f"health took {health_elapsed:.3f}s — event loop likely blocked"


def test_detected_language_passthrough(client, monkeypatch):
    monkeypatch.setattr("assistant.api.routers.speech.whisper_available", lambda key: True)

    def fake(*a, **k):
        return TranscribeResult(
            text="ሰላም",
            language_used="am",
            timings={"whisper_ms": 5.0, "total_ms": 5.0},
        )

    monkeypatch.setattr("assistant.api.routers.speech.transcribe_audio_timed", fake)
    res = client.post(
        "/api/transcribe",
        files={"audio": ("speech.webm", b"fake-audio-bytes", "audio/webm")},
        data={"language": "auto"},
    )
    assert res.status_code == 200
    assert res.json()["language_used"] == "am"


@pytest.mark.live
def test_live_whisper_skipped_without_key_or_clip():
    """Live clips must be recorded by a human; skip when absent."""
    import os
    from pathlib import Path

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("WHISPER_API_KEY")
    clip = Path(__file__).resolve().parent / "fixtures" / "whisper_en.wav"
    if not key or not clip.exists():
        pytest.skip("Live Whisper requires OPENAI_API_KEY/WHISPER_API_KEY and tests/fixtures/whisper_en.wav")
    from assistant.infrastructure.speech import transcribe_audio

    text, used, warning = transcribe_audio(
        clip.read_bytes(),
        filename="whisper_en.wav",
        mime_type="audio/wav",
        language_hint="en",
        api_key=key,
    )
    assert text.strip()
    assert used in ("en", "auto") or used.startswith("en")
