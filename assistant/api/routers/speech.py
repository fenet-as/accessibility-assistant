"""Speech-to-text endpoint (Whisper) for the widget voice button."""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, Response
from starlette.concurrency import run_in_threadpool

from assistant.api.dependencies import get_container
from assistant.container import Container
from assistant.infrastructure.speech import (
    SttAuthError,
    SttBadAudioError,
    SttError,
    SttTimeoutError,
    SttUpstreamError,
    stt_status,
    transcribe_audio_timed,
    validate_audio_upload,
    whisper_available,
)

router = APIRouter(prefix="/api", tags=["Speech"])


@router.post("/transcribe")
async def transcribe(
    request: Request,
    response: Response,
    audio: UploadFile = File(..., description="Recorded audio (webm, wav, mpeg, …)"),
    language: str = Form(default="auto"),
    container: Container = Depends(get_container),
) -> Dict[str, Any]:
    settings = container.settings
    key = settings.openai_api_key or settings.whisper_api_key
    if not whisper_available(key):
        raise HTTPException(
            status_code=503,
            detail="Server speech recognition is not configured. Set OPENAI_API_KEY or WHISPER_API_KEY and install openai.",
        )

    client_key = request.client.host if request.client else "unknown"
    limited = container.rate_limiter.check(ip=client_key, kind="stt")
    if not limited.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many transcription requests. Try again in a minute.",
            headers={"Retry-After": str(limited.retry_after or 60)},
        )

    t0 = time.perf_counter()
    payload = await audio.read()
    receive_ms = round((time.perf_counter() - t0) * 1000, 1)
    mime = audio.content_type or "audio/webm"
    name = audio.filename or "speech.webm"
    # Never log or persist audio bytes.

    t_val = time.perf_counter()
    problem = validate_audio_upload(
        payload=payload,
        filename=name,
        mime_type=mime,
        max_bytes=settings.stt_max_bytes,
        max_seconds=settings.stt_max_seconds,
    )
    validate_ms = round((time.perf_counter() - t_val) * 1000, 1)
    if problem:
        status = 413 if "too large" in problem.lower() or "longer than" in problem.lower() else 400
        if container.usage:
            container.usage.record_stt_error("validation")
        raise HTTPException(status_code=status, detail=problem)

    lang_hint = (language or "auto").strip().lower()
    timeout = float(getattr(settings, "stt_timeout_seconds", 30) or 30)

    try:
        # Offload sync OpenAI SDK so /api/chat is never blocked by Whisper.
        result = await run_in_threadpool(
            transcribe_audio_timed,
            payload,
            filename=name,
            mime_type=mime,
            language_hint=lang_hint,
            api_key=key,
            model=settings.whisper_model,
            timeout=timeout,
        )
    except RuntimeError as exc:
        if container.usage:
            container.usage.record_stt_error("sdk")
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except SttTimeoutError as exc:
        if container.usage:
            container.usage.record_stt_error("timeout")
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    except SttAuthError as exc:
        if container.usage:
            container.usage.record_stt_error("auth")
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    except SttBadAudioError as exc:
        if container.usage:
            container.usage.record_stt_error("bad_audio")
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    except SttError as exc:
        if container.usage:
            container.usage.record_stt_error(exc.code)
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    except Exception as exc:
        if container.usage:
            container.usage.record_stt_error("upstream")
        raise HTTPException(status_code=502, detail="Transcription failed") from exc

    if not result.text:
        if container.usage:
            container.usage.record_stt_error("empty")
        raise HTTPException(status_code=422, detail="No speech detected in recording")

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    timings = {
        "receive_ms": receive_ms,
        "validate_ms": validate_ms,
        **(result.timings or {}),
        "total_ms": total_ms,
    }
    if container.usage:
        container.usage.record_stt_latency(timings.get("whisper_ms") or total_ms)
        container.usage.record_stt_success()

    response.headers["Server-Timing"] = (
        f"receive;dur={receive_ms}, validate;dur={validate_ms}, "
        f"whisper;dur={timings.get('whisper_ms', 0)}, total;dur={total_ms}"
    )

    body: Dict[str, Any] = {
        "text": result.text,
        "language_hint": lang_hint,
        "language_used": result.language_used,
        "provider": "whisper",
        "status": stt_status(settings),
        "timings": timings,
    }
    if result.language_warning:
        body["language_warning"] = result.language_warning
    return body
