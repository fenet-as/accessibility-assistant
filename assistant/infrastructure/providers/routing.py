"""When to use extractive FAQ vs generative cloud/local models."""

from __future__ import annotations

import re
from typing import List, Optional

from assistant.domain.models import ConversationTurn, Passage

_EXPLANATION_RE = re.compile(
    r"\b(why|how|explain|compare|difference|versus|vs\.?|elaborate|describe|meaning of)\b",
    re.I,
)
_ETHIOPIC_EXPLAIN = re.compile(r"(ለምን|እንዴት|ማብራሪያ|ልዩነት|አብራራ)")


def prefers_extractive_answer(
    question: str,
    passages: List[Passage],
    *,
    confidence: float,
    simple: bool,
    history: Optional[List[ConversationTurn]] = None,
    high_confidence: float = 0.6,
) -> bool:
    """High-confidence definitional questions get zero-token extractive answers first."""
    if history:
        return False
    if not passages:
        return False
    if simple and confidence >= high_confidence:
        return True
    if confidence >= 0.85 and not (_EXPLANATION_RE.search(question) or _ETHIOPIC_EXPLAIN.search(question)):
        return True
    if confidence >= high_confidence and question.strip().lower().startswith(("what is", "who is", "define")):
        return True
    return False