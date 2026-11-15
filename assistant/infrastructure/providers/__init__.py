"""Pluggable AI providers. Select one with the AI_PROVIDER environment variable."""

from typing import Optional

from assistant.config import Settings
from assistant.domain.ports import AIProvider
from assistant.infrastructure.providers.composite import RoutedAIProvider
from assistant.infrastructure.providers.faq import OfflineFAQProvider
from assistant.infrastructure.providers.gemini import GeminiProvider
from assistant.infrastructure.providers.local import LocalModelProvider
from assistant.infrastructure.usage import UsageTracker


def build_provider(settings: Settings, usage: Optional[UsageTracker] = None) -> AIProvider:
    # Offline FAQ uses translations embedded on each chunk; optional legacy file if present.
    faq_path = settings.faq_translations_path
    faq = OfflineFAQProvider(faq_path if faq_path and faq_path.exists() else None)
    if settings.ai_provider == "local":
        return LocalModelProvider(
            settings.local_model_url,
            settings.local_model_name,
            faq,
            max_context_tokens=settings.max_context_tokens,
            max_output_tokens=settings.max_output_tokens,
            usage=usage,
        )
    if settings.ai_provider == "cloud":
        gemini = GeminiProvider(
            settings.gemini_api_key,
            settings.gemini_model,
            faq,
            max_context_tokens=settings.max_context_tokens,
            max_output_tokens=settings.max_output_tokens,
            max_chars_per_passage=settings.max_chars_per_passage,
            timeout_seconds=settings.gemini_timeout_seconds,
            usage=usage,
        )
        return RoutedAIProvider(
            faq,
            gemini,
            usage=usage,
            prefer_extractive=settings.prefer_extractive,
        )
    return faq


__all__ = [
    "build_provider",
    "OfflineFAQProvider",
    "GeminiProvider",
    "LocalModelProvider",
    "RoutedAIProvider",
]