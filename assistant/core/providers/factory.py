"""Factory to instantiate AI providers based on environment configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

from assistant.core.models import AIProvider
from assistant.core.providers.faq_provider import OfflineFAQProvider
from assistant.core.providers.cloud_provider import CloudProvider

# Automatically load environment variables from .env if present
base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(base_dir / ".env")
load_dotenv(base_dir / "assistant" / ".env")


def get_ai_provider() -> AIProvider:
    provider_name = os.getenv("AI_PROVIDER", "faq").lower().strip()
    if provider_name == "cloud":
        return CloudProvider()
    return OfflineFAQProvider()

