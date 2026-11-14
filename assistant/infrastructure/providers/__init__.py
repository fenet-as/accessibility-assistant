"""Pluggable AI providers. Select one with the AI_PROVIDER environment variable."""

from assistant.config import Settings
from assistant.domain.ports import AIProvider
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider


def build_provider(settings: Settings) -> AIProvider:
    offline = OfflineFAQProvider(settings.faq_translations_path)
    if settings.ai_provider == "cloud":
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, fallback=offline)
    return offline


__all__ = ["build_provider", "OfflineFAQProvider", "GeminiProvider"]
