"""Server-side speech-to-text (OpenAI Whisper) for languages browsers transcribe poorly."""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

WHISPER_LANG_MAP = {
    "en": "en",
    "am": "am",
    "ti": "ti",
    "om": "om",
    "so": "so",
    "ar": "ar",
    "auto": "",
}


def whisper_available(api_key: str) -> bool:
    return bool(api_key and api_key.strip())


def stt_status(settings) -> dict:
    key = settings.openai_api_key or settings.whisper_api_key
    available = whisper_available(key)
    return {
        "server_stt": available,
        "provider": "whisper" if available else "browser",
        "model": settings.whisper_model if available else None,
    }


def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str,
    mime_type: str,
    language_hint: str = "auto",
    api_key: str,
    model: str = "whisper-1",
) -> Tuple[str, str]:
    """Return (transcript, language_used). Raises on failure."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package not installed") from exc

    client = OpenAI(api_key=api_key)
    whisper_lang = WHISPER_LANG_MAP.get(language_hint, "") or WHISPER_LANG_MAP.get(language_hint[:2], "")
    kwargs = {"model": model, "temperature": 0}
    if whisper_lang:
        kwargs["language"] = whisper_lang

    file_tuple = (filename or "speech.webm", audio_bytes, mime_type or "audio/webm")
    try:
        result = client.audio.transcriptions.create(file=file_tuple, **kwargs)
    except Exception:
        logger.warning("Whisper transcription failed", exc_info=True)
        raise

    text = (getattr(result, "text", None) or "").strip()
    detected = whisper_lang or language_hint if language_hint != "auto" else "auto"
    return text, detected