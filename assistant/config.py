"""Typed application settings, read once from the environment and `.env` files.

Load order (highest priority first):
1. Real OS / process environment variables (Docker, CI, shell exports).
2. Project-root `.env` (PROJECT_ROOT / ".env").
3. Package `.env` (assistant/.env) for legacy local overrides.

`get_settings()` and `get_container()` are process-cached. After editing `.env`,
fully stop and restart the API process — `uvicorn --reload` does not watch `.env`.
"""

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
_ROOT_ENV = PROJECT_ROOT / ".env"
_PKG_ENV = PACKAGE_DIR / ".env"
load_dotenv(_ROOT_ENV, override=False)
load_dotenv(_PKG_ENV, override=False)


def _resolve_path(value: str, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    ai_provider: str = "cloud"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: float = 45.0
    prefer_extractive: bool = False

    host_url: str = "http://localhost:8000"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    database_path: Path = DATA_DIR / "assistant.db"
    chunks_path: Path = DATA_DIR / "chunks.json"
    jobs_path: Path = DATA_DIR / "jobs.json"
    faq_translations_path: Path = DATA_DIR / "faq_translations.json"
    savanna_dir: Path = PROJECT_ROOT / "savanna-static"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_staff_chat_id: str = ""
    jitsi_base_url: str = "https://meet.jit.si"
    admin_token: str = ""
    allow_open_admin: bool = False
    ingest_max_content_chars: int = 500_000
    log_question_text: str = "redacted"

    africas_talking_api_key: str = ""
    africas_talking_username: str = "sandbox"
    android_gateway_url: str = ""
    android_gateway_token: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    default_scope: str = "course:va-1"
    relevance_threshold: float = 0.35
    # education: course + VA/freelancing/remote-work/digital-skills/career topics; course_only; open
    course_scope_policy: str = "education"

    enable_exact_cache: bool = True
    redis_url: str = ""
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 4096

    max_context_tokens: int = 800
    max_output_tokens: int = 600
    max_chars_per_passage: int = 1500

    local_model_url: str = ""
    local_model_name: str = "local-model"

    openai_api_key: str = ""
    whisper_api_key: str = ""
    whisper_model: str = "whisper-1"
    stt_max_bytes: int = 8 * 1024 * 1024
    stt_max_seconds: int = 60
    stt_timeout_seconds: float = 30.0

    rate_limit_session_per_min: int = 20
    rate_limit_ip_per_min: int = 60
    rate_limit_stt_per_min: int = 6
    daily_token_budget: int = 0
    daily_cost_budget_usd: float = 0.0


def load_settings() -> Settings:
    env = os.environ
    return Settings(
        ai_provider=env.get("AI_PROVIDER", "cloud").strip().lower(),
        gemini_api_key=env.get("GEMINI_API_KEY", ""),
        gemini_model=env.get("GEMINI_MODEL", "gemini-3.5-flash"),
        gemini_timeout_seconds=float(env.get("GEMINI_TIMEOUT_SECONDS", "45")),
        prefer_extractive=env.get("PREFER_EXTRACTIVE", "false").strip().lower() in ("1", "true", "yes"),
        host_url=env.get("HOST_URL", "http://localhost:8000").rstrip("/"),
        cors_origins=_csv(env.get("CORS_ORIGINS", "*")) or ["*"],
        database_path=_resolve_path(env.get("DATABASE_PATH", ""), DATA_DIR / "assistant.db"),
        chunks_path=_resolve_path(env.get("CHUNKS_PATH", ""), DATA_DIR / "chunks.json"),
        jobs_path=_resolve_path(env.get("JOBS_PATH", ""), DATA_DIR / "jobs.json"),
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_webhook_secret=env.get("TELEGRAM_WEBHOOK_SECRET", "").strip(),
        telegram_staff_chat_id=env.get("TELEGRAM_STAFF_CHAT_ID", "").strip(),
        jitsi_base_url=env.get("JITSI_BASE_URL", "https://meet.jit.si").rstrip("/"),
        admin_token=env.get("ADMIN_TOKEN", ""),
        allow_open_admin=env.get("ALLOW_OPEN_ADMIN", "false").strip().lower() in ("1", "true", "yes"),
        ingest_max_content_chars=int(env.get("INGEST_MAX_CONTENT_CHARS", "500000")),
        log_question_text=env.get("LOG_QUESTION_TEXT", "redacted").strip().lower(),
        africas_talking_api_key=env.get("AFRICAS_TALKING_API_KEY", ""),
        africas_talking_username=env.get("AFRICAS_TALKING_USERNAME", "sandbox"),
        android_gateway_url=env.get("ANDROID_GATEWAY_URL", "").rstrip("/"),
        android_gateway_token=env.get("ANDROID_GATEWAY_TOKEN", ""),
        twilio_account_sid=env.get("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=env.get("TWILIO_AUTH_TOKEN", ""),
        twilio_phone_number=env.get("TWILIO_PHONE_NUMBER", ""),
        course_scope_policy=env.get("COURSE_SCOPE_POLICY", "education").strip().lower() or "education",
        enable_exact_cache=env.get("ENABLE_EXACT_CACHE", "true").strip().lower() in ("1", "true", "yes"),
        redis_url=env.get("REDIS_URL", "").strip(),
        cache_ttl_seconds=int(env.get("CACHE_TTL_SECONDS", "3600")),
        cache_max_entries=int(env.get("CACHE_MAX_ENTRIES", "4096")),
        max_context_tokens=int(env.get("MAX_CONTEXT_TOKENS", "800")),
        max_output_tokens=int(env.get("MAX_OUTPUT_TOKENS", "600")),
        max_chars_per_passage=int(env.get("MAX_CHARS_PER_PASSAGE", "1500")),
        local_model_url=env.get("LOCAL_MODEL_URL", "").strip().rstrip("/"),
        local_model_name=env.get("LOCAL_MODEL_NAME", "local-model"),
        openai_api_key=env.get("OPENAI_API_KEY", "").strip(),
        whisper_api_key=env.get("WHISPER_API_KEY", "").strip(),
        whisper_model=env.get("WHISPER_MODEL", "whisper-1"),
        stt_max_bytes=int(env.get("STT_MAX_BYTES", str(8 * 1024 * 1024))),
        stt_max_seconds=int(env.get("STT_MAX_SECONDS", "60")),
        stt_timeout_seconds=float(env.get("STT_TIMEOUT_SECONDS", "30")),
        rate_limit_session_per_min=int(env.get("RATE_LIMIT_SESSION_PER_MIN", "20")),
        rate_limit_ip_per_min=int(env.get("RATE_LIMIT_IP_PER_MIN", "60")),
        rate_limit_stt_per_min=int(env.get("RATE_LIMIT_STT_PER_MIN", "6")),
        daily_token_budget=int(env.get("DAILY_TOKEN_BUDGET", "0")),
        daily_cost_budget_usd=float(env.get("DAILY_COST_BUDGET_USD", "0")),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def env_file_paths() -> List[str]:
    """Paths checked for dotenv files (for health/config diagnostics)."""
    return [str(_ROOT_ENV), str(_PKG_ENV)]


def safe_ai_config_summary(settings: Settings) -> dict:
    """Non-secret AI configuration snapshot for logs and /api/health."""
    return {
        "ai_provider": settings.ai_provider,
        "gemini_model": settings.gemini_model,
        "gemini_key_configured": bool((settings.gemini_api_key or "").strip()),
        "prefer_extractive": settings.prefer_extractive,
        "exact_cache_enabled": settings.enable_exact_cache,
        "redis_configured": bool((settings.redis_url or "").strip()),
        "course_scope_policy": settings.course_scope_policy,
        "gemini_timeout_seconds": settings.gemini_timeout_seconds,
        "env_files": env_file_paths(),
        "note": "Restart the API process after changing .env; settings are loaded once at startup.",
    }
