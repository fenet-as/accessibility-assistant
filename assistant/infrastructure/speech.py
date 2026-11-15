"""Server-side speech-to-text (OpenAI Whisper) for languages browsers transcribe poorly."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Whisper accepts ISO-639-1 for a subset of languages. ti/om are not supported:
# omit the language hint so Whisper auto-detects (often Amharic/English nearby).
WHISPER_LANG_MAP = {
    "en": "en",
    "am": "am",
    "so": "so",
    "ar": "ar",
    "auto": "",
}
WHISPER_UNSUPPORTED_HINTS = frozenset({"ti", "om"})

ALLOWED_AUDIO_MIMES = frozenset({
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "video/webm",  # Chrome often labels MediaRecorder blobs this way
})

ALLOWED_AUDIO_EXTENSIONS = frozenset({".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4"})

_CLIENT_LOCK = threading.Lock()
_CLIENT_CACHE: Dict[str, Any] = {}


class SttError(Exception):
    """Base STT error with a stable machine-readable code."""

    code = "upstream"
    http_status = 502

    def __init__(self, message: str = "Transcription failed"):
        super().__init__(message)
        self.message = message


class SttTimeoutError(SttError):
    code = "timeout"
    http_status = 504


class SttAuthError(SttError):
    code = "auth"
    http_status = 502


class SttBadAudioError(SttError):
    code = "bad_audio"
    http_status = 400


class SttUpstreamError(SttError):
    code = "upstream"
    http_status = 502


@dataclass
class TranscribeResult:
    text: str
    language_used: str
    language_warning: Optional[str] = None
    timings: Dict[str, float] = field(default_factory=dict)


def openai_sdk_available() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def whisper_available(api_key: str) -> bool:
    return bool(api_key and api_key.strip()) and openai_sdk_available()


def stt_status(settings) -> dict:
    key = settings.openai_api_key or settings.whisper_api_key
    available = whisper_available(key)
    return {
        "server_stt": available,
        "provider": "whisper" if available else "browser",
        "model": settings.whisper_model if available else None,
        "sdk_installed": openai_sdk_available(),
        "key_configured": bool((key or "").strip()),
    }


def resolve_whisper_language(language_hint: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (whisper_language_or_None, warning_or_None)."""
    hint = (language_hint or "auto").strip().lower()
    if hint in ("", "auto"):
        return None, None
    if hint in WHISPER_UNSUPPORTED_HINTS:
        return None, (
            f"Whisper has no dedicated model for '{hint}'; "
            "using auto-detect. Accuracy may be lower."
        )
    mapped = WHISPER_LANG_MAP.get(hint) or WHISPER_LANG_MAP.get(hint[:2])
    if mapped:
        return mapped, None
    return None, f"Unknown language hint '{hint}'; using auto-detect."


def validate_audio_upload(
    *,
    payload: bytes,
    filename: str,
    mime_type: str,
    max_bytes: int,
    max_seconds: int,
) -> Optional[str]:
    """Return an error message if the upload is invalid; otherwise None."""
    if not payload:
        return "Empty audio upload"
    if len(payload) > max_bytes:
        return "Audio file too large"
    mime = (mime_type or "").split(";")[0].strip().lower()
    name = (filename or "").lower()
    ext_ok = any(name.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS)
    mime_ok = mime in ALLOWED_AUDIO_MIMES or mime.startswith("audio/")
    if not mime_ok and not ext_ok:
        return f"Unsupported audio type '{mime_type or filename}'"
    # Rough duration guard when container headers are absent: reject absurdly large
    # payloads for the configured max duration (≈ 32 kbps floor for compressed audio).
    min_bytes_per_sec = 2000
    if max_seconds > 0 and len(payload) > max_seconds * min_bytes_per_sec * 8:
        return f"Audio appears longer than the {max_seconds}s limit"
    return None


class SttRateLimiter:
    """Simple in-process sliding window; Milestone 6 replaces this with Redis."""

    def __init__(self, max_per_minute: int = 6):
        self.max_per_minute = max_per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.max_per_minute:
            return False
        window.append(now)
        return True


_STT_LIMITER = SttRateLimiter()


def stt_rate_limiter() -> SttRateLimiter:
    return _STT_LIMITER


def get_openai_client(api_key: str, *, timeout: float = 30.0):
    """Return a process-wide cached OpenAI client (connection reuse)."""
    key = (api_key or "").strip()
    cache_key = f"{key[:12]}:{timeout}"
    with _CLIENT_LOCK:
        client = _CLIENT_CACHE.get(cache_key)
        if client is not None:
            return client
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=timeout)
        _CLIENT_CACHE[cache_key] = client
        return client


def clear_openai_client_cache() -> None:
    with _CLIENT_LOCK:
        _CLIENT_CACHE.clear()


def _map_openai_error(exc: BaseException) -> SttError:
    name = type(exc).__name__
    message = str(exc) or name
    lower = message.lower()
    if "timeout" in name.lower() or "timeout" in lower or "timed out" in lower:
        return SttTimeoutError("Transcription timed out")
    if "auth" in name.lower() or "unauthorized" in lower or "invalid api key" in lower or "401" in lower:
        return SttAuthError("Speech recognition authentication failed")
    if "invalid" in lower and ("file" in lower or "audio" in lower or "format" in lower):
        return SttBadAudioError("Audio could not be decoded")
    return SttUpstreamError("Transcription failed")


def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str,
    mime_type: str,
    language_hint: str = "auto",
    api_key: str,
    model: str = "whisper-1",
    timeout: float = 30.0,
) -> Tuple[str, str, Optional[str]]:
    """Return (transcript, language_used, language_warning). Raises on failure.

    Backwards-compatible wrapper around transcribe_audio_timed.
    """
    result = transcribe_audio_timed(
        audio_bytes,
        filename=filename,
        mime_type=mime_type,
        language_hint=language_hint,
        api_key=api_key,
        model=model,
        timeout=timeout,
    )
    return result.text, result.language_used, result.language_warning


def transcribe_audio_timed(
    audio_bytes: bytes,
    *,
    filename: str,
    mime_type: str,
    language_hint: str = "auto",
    api_key: str,
    model: str = "whisper-1",
    timeout: float = 30.0,
) -> TranscribeResult:
    """Transcribe with per-stage timings and typed errors. Never logs audio bytes."""
    try:
        import openai  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("openai package not installed") from exc

    timings: Dict[str, float] = {}
    t0 = time.perf_counter()
    whisper_lang, warning = resolve_whisper_language(language_hint)
    timings["prepare_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    client = get_openai_client(api_key, timeout=timeout)
    kwargs: Dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "response_format": "verbose_json",
    }
    if whisper_lang:
        kwargs["language"] = whisper_lang

    file_tuple = (filename or "speech.webm", audio_bytes, mime_type or "audio/webm")
    t_whisper = time.perf_counter()
    try:
        result = client.audio.transcriptions.create(file=file_tuple, **kwargs)
    except Exception as exc:
        timings["whisper_ms"] = round((time.perf_counter() - t_whisper) * 1000, 1)
        timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        logger.warning(
            "Whisper transcription failed code=%s (audio not logged)",
            type(exc).__name__,
            exc_info=True,
        )
        mapped = _map_openai_error(exc)
        mapped.timings = timings  # type: ignore[attr-defined]
        raise mapped from exc

    timings["whisper_ms"] = round((time.perf_counter() - t_whisper) * 1000, 1)

    text = (getattr(result, "text", None) or "").strip()
    detected = getattr(result, "language", None)
    if isinstance(detected, str) and detected.strip():
        language_used = detected.strip().lower()[:8]
    elif whisper_lang:
        language_used = whisper_lang
    elif language_hint not in ("", "auto") and language_hint not in WHISPER_UNSUPPORTED_HINTS:
        language_used = language_hint
    else:
        language_used = "auto"

    timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return TranscribeResult(
        text=text,
        language_used=language_used,
        language_warning=warning,
        timings=timings,
    )
