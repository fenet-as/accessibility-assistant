"""Verified course-name aliases embedded in code (no separate JSON catalog).

Every key must match a canonical ``scope`` from the chunk store / ``chunks.json``.
Translations are curated — not machine-invented.
"""

from __future__ import annotations

from typing import Any, Dict

# Linked to scopes in the live knowledge base. Orphan keys are ignored at runtime.
DEFAULT_COURSE_ALIASES: Dict[str, Any] = {
    "course:va-1": {
        "canonical_name": "VA-1: VA Foundations & Professional Identity",
        "search_names": [
            "Virtual Assistant",
            "VA Foundations",
            "VA Foundations & Professional Identity",
            "VA Foundations and Professional Identity",
        ],
        "abbreviations": ["VA", "VA-1", "VA1"],
        "aliases": {
            "en": [
                "virtual assistant",
                "virtual assistant course",
                "VA course",
                "VA foundations",
                "virtual assistant training",
            ],
            "am": [
                "ቨርቹዋል ረዳት",
                "የቨርቹዋል ረዳት",
                "ቨርቹዋል ረዳት ኮርስ",
                "የቨርቹዋል ረዳት ትምህርት",
            ],
            "ti": [
                "ቨርቹዋል ሓጋዚ",
                "ቨርቹዋል ሓጋዚ ትምህርቲ",
                "ናይ ቨርቹዋል ሓጋዚ",
            ],
            "om": [
                "gargaaraa virtualii",
                "gargaaraa virtuaalaa",
                "gargaaraa virtualii course",
                "koorsii gargaaraa virtualii",
            ],
            "so": [
                "kaaliye virtual",
                "kaaliyaha virtual",
                "koorsada kaaliyaha virtual",
                "casharka kaaliye virtual",
            ],
            "ar": [
                "المساعد الافتراضي",
                "مساعد افتراضي",
                "دورة المساعد الافتراضي",
                "دورة مساعد افتراضي",
            ],
        },
        "spelling_variants": [
            "virtul assistant",
            "virtual asistant",
            "virtual assistent",
            "virtual assitant",
            "virtua assistant",
            "virtal assistant",
            "virtual asistnt",
            "virtuall assistant",
        ],
    }
}
