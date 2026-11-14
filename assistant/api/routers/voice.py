"""Voice endpoints: Addis AI Speech-to-Text and Text-to-Speech with client fallback."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from assistant.api.dependencies import get_container
from assistant.container import Container

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.get("/status")
def voice_status(container: Container = Depends(get_container)):
    """Check availability of Addis AI voice services."""
    return {
        "provider": "addis_ai",
        "configured": container.addis_ai.is_configured,
        "tts_languages": ["am", "ti", "om", "en", "sid", "wal", "sw"],
        "stt_languages": ["am", "om"],
    }


@router.get("/speak")
def speak(
    text: str = Query(..., min_length=1, max_length=1500),
    language: str = Query(default="am"),
    container: Container = Depends(get_container),
):
    """Generate natural speech audio (MP3) for text using Addis AI Voices."""
    if not container.addis_ai.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Addis AI voice synthesis is not configured",
        )

    audio_bytes = container.addis_ai.synthesize(text=text, language=language)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate speech with Addis AI",
        )

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/transcribe")
async def transcribe(
    request: Request,
    language: str = Query(default="am"),
    container: Container = Depends(get_container),
):
    """Transcribe uploaded audio clip using Addis Scribe."""
    if not container.addis_ai.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Addis AI Scribe transcription is not configured",
        )

    content = await request.body()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio data is empty",
        )

    content_type = request.headers.get("content-type", "audio/webm")
    text = container.addis_ai.transcribe(
        audio_bytes=content,
        language=language,
        filename="audio.webm",
        content_type=content_type,
    )

    if text is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Addis AI Scribe transcription failed",
        )

    return {"text": text, "language": language}
