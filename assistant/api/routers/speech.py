"""Speech-to-text endpoint (Whisper) for the widget voice button."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from assistant.api.dependencies import get_container
from assistant.container import Container
from assistant.infrastructure.speech import stt_status, transcribe_audio, whisper_available

router = APIRouter(prefix="/api", tags=["Speech"])


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(..., description="Recorded audio (webm, wav, mpeg, …)"),
    language: str = Form(default="auto"),
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    settings = container.settings
    key = settings.openai_api_key or settings.whisper_api_key
    if not whisper_available(key):
        raise HTTPException(
            status_code=503,
            detail="Server speech recognition is not configured. Set OPENAI_API_KEY or WHISPER_API_KEY.",
        )

    payload = await audio.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    if len(payload) > settings.stt_max_bytes:
        raise HTTPException(status_code=413, detail="Audio file too large")

    lang_hint = (language or "auto").strip().lower()
    mime = audio.content_type or "audio/webm"
    name = audio.filename or "speech.webm"
    try:
        text, lang_used = transcribe_audio(
            payload,
            filename=name,
            mime_type=mime,
            language_hint=lang_hint,
            api_key=key,
            model=settings.whisper_model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Transcription failed") from exc

    if not text:
        raise HTTPException(status_code=422, detail="No speech detected in recording")

    return {
        "text": text,
        "language_hint": lang_hint,
        "language_used": lang_used,
        "provider": "whisper",
    }

