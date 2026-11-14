"""Typed application settings, read once from the environment and `.env` files."""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR / "data"

# Real environment variables always win over .env files (Docker, CI, tests).
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PACKAGE_DIR / ".env", override=False)


def _resolve_path(value: str, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    ai_provider: str = "faq"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    host_url: str = "http://localhost:8000"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    database_path: Path = DATA_DIR / "assistant.db"
    chunks_path: Path = DATA_DIR / "chunks.json"
    jobs_path: Path = DATA_DIR / "jobs.json"
    faq_translations_path: Path = DATA_DIR / "faq_translations.json"
    savanna_dir: Path = PROJECT_ROOT / "savanna-static"

    telegram_bot_token: str = ""
    jitsi_base_url: str = "https://meet.jit.si"
    admin_token: str = ""

    africas_talking_api_key: str = ""
    africas_talking_username: str = "sandbox"
    android_gateway_url: str = ""
    android_gateway_token: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    default_scope: str = "course:va-1"
    relevance_threshold: float = 0.35
    answer_cache_size: int = 1024


def load_settings() -> Settings:
    env = os.environ
    return Settings(
        ai_provider=env.get("AI_PROVIDER", "faq").strip().lower(),
        gemini_api_key=env.get("GEMINI_API_KEY", ""),
        gemini_model=env.get("GEMINI_MODEL", "gemini-2.5-flash"),
        host_url=env.get("HOST_URL", "http://localhost:8000").rstrip("/"),
        cors_origins=_csv(env.get("CORS_ORIGINS", "*")) or ["*"],
        database_path=_resolve_path(env.get("DATABASE_PATH", ""), DATA_DIR / "assistant.db"),
        chunks_path=_resolve_path(env.get("CHUNKS_PATH", ""), DATA_DIR / "chunks.json"),
        jobs_path=_resolve_path(env.get("JOBS_PATH", ""), DATA_DIR / "jobs.json"),
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
        jitsi_base_url=env.get("JITSI_BASE_URL", "https://meet.jit.si").rstrip("/"),
        admin_token=env.get("ADMIN_TOKEN", ""),
        africas_talking_api_key=env.get("AFRICAS_TALKING_API_KEY", ""),
        africas_talking_username=env.get("AFRICAS_TALKING_USERNAME", "sandbox"),
        android_gateway_url=env.get("ANDROID_GATEWAY_URL", "").rstrip("/"),
        android_gateway_token=env.get("ANDROID_GATEWAY_TOKEN", ""),
        twilio_account_sid=env.get("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=env.get("TWILIO_AUTH_TOKEN", ""),
        twilio_phone_number=env.get("TWILIO_PHONE_NUMBER", ""),
        answer_cache_size=int(env.get("ANSWER_CACHE_SIZE", "1024")),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
