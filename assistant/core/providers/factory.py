"""Factory to instantiate AI providers based on environment configuration."""

import os
from assistant.core.models import AIProvider
from assistant.core.providers.faq_provider import OfflineFAQProvider
from assistant.core.providers.cloud_provider import CloudProvider


def get_ai_provider() -> AIProvider:
    provider_name = os.getenv("AI_PROVIDER", "faq").lower().strip()
    if provider_name == "cloud":
        return CloudProvider()
    return OfflineFAQProvider()
