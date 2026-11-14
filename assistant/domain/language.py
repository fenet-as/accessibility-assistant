"""Language detection for the two supported languages (Amharic and English)."""

import re

SUPPORTED_LANGUAGES = ("am", "en")
ETHIOPIC_PATTERN = re.compile(r"[\u1200-\u137F]")


def contains_ethiopic(text: str) -> bool:
    return bool(ETHIOPIC_PATTERN.search(text))


def detect_language(text: str, requested: str = "auto") -> str:
    """Honour an explicit `am`/`en` choice; otherwise infer from the script used."""
    if requested in SUPPORTED_LANGUAGES:
        return requested
    return "am" if contains_ethiopic(text) else "en"
