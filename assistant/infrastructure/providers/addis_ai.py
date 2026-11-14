"""Addis AI client for local Ethiopian Speech-to-Text and Text-to-Speech.

Supports Amharic (am), Tigrinya (ti), and Afaan Oromo (om) with native Ethiopian
voice models and Scribe transcription.
"""

import base64
import io
import json
import logging
import urllib.error
import urllib.request
import uuid
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://api.addisassistant.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SavannaAssistant/1.0"

# Default natural voices per language on Addis AI
VOICE_MAP: Dict[str, str] = {
    "am": "am-hamen",       # Amharic female (Hamen - conversational)
    "ti": "ti-freweyni",    # Tigrinya female (Freweyni)
    "om": "om-bikila",      # Afaan Oromo male (Bikila)
    "en": "en-emma",        # English female (Emma)
    "sid": "sid-selam",     # Sidama female
    "wal": "wal-almaz",     # Wolaytta female
    "sw": "sw-zawadi",      # Swahili female
}


class AddisAIClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def synthesize(self, text: str, language: str = "am") -> Optional[bytes]:
        """Convert text to speech audio bytes (MP3) using Addis AI Voices."""
        if not self.is_configured:
            logger.debug("Addis AI is not configured (missing API key).")
            return None

        clean_text = (text or "").strip()
        if not clean_text:
            return None

        lang = language.lower()
        voice_id = VOICE_MAP.get(lang, VOICE_MAP["am"])
        url = f"{self.base_url}/api/v1/voice/generations"

        payload = json.dumps({
            "client_request_id": str(uuid.uuid4()),
            "voice_id": voice_id,
            "language": lang,
            "text": clean_text[:1000],  # safety limit for single speech bubble
        }).encode("utf-8")

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
                d = data.get("data", {})
                raw_audio = d.get("audio", "")
                if raw_audio and "," in raw_audio:
                    # Data URI format: data:audio/mpeg;base64,...
                    return base64.b64decode(raw_audio.split(",")[-1])
                elif d.get("audio_url"):
                    # Fallback: fetch from CDN
                    cdn_req = urllib.request.Request(d["audio_url"], headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(cdn_req, timeout=10) as cdn_res:
                        return cdn_res.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning("Addis AI TTS generation error HTTP %s: %s", e.code, err_body)
        except Exception as e:
            logger.warning("Addis AI TTS generation failed: %s", e)

        return None

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "am",
        filename: str = "audio.webm",
        content_type: str = "audio/webm",
    ) -> Optional[str]:
        """Transcribe speech audio to text using Addis Scribe."""
        if not self.is_configured:
            logger.debug("Addis AI is not configured (missing API key).")
            return None

        if not audio_bytes:
            return None

        # Addis Scribe language support: 'am' (Amharic) or 'om' (Oromo)
        scribe_lang = "om" if language.lower() in ("om", "oromo") else "am"
        req_id = uuid.uuid4().hex
        url = f"{self.base_url}/api/v1/scribe/transcribe?backend=turbo&language={scribe_lang}&request_id={req_id}"

        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(
            f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.write(audio_bytes)
        body.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT,
        }

        try:
            req = urllib.request.Request(url, data=body.getvalue(), headers=headers)
            with urllib.request.urlopen(req, timeout=20) as res:
                data = json.loads(res.read().decode("utf-8"))
                text = data.get("data", {}).get("text", "")
                return text.strip() if text else None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning("Addis AI Scribe transcription error HTTP %s: %s", e.code, err_body)
        except Exception as e:
            logger.warning("Addis AI Scribe transcription failed: %s", e)

        return None
