"""Approximate token budgeting for prompts (no tokenizer dependency)."""

from __future__ import annotations

from typing import List

from assistant.domain.models import ConversationTurn, Passage

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // _CHARS_PER_TOKEN)


def trim_passages_for_context(
    passages: List[Passage],
    language: str,
    *,
    max_passages: int = 3,
    max_chars_per_passage: int = 1500,
    max_context_tokens: int = 800,
) -> List[Passage]:
    """Return at most max_passages passages whose combined text fits the context budget."""
    selected: List[Passage] = []
    used_tokens = 0
    for passage in passages[:max_passages]:
        body = passage.text[:max_chars_per_passage]
        translated = (passage.translations or {}).get(language)
        if translated:
            body = f"{translated}\n{body}"
        header = f"{passage.title} | {passage.section}"
        cost = estimate_tokens(header) + estimate_tokens(body)
        if selected and used_tokens + cost > max_context_tokens:
            break
        if not selected or used_tokens + cost <= max_context_tokens:
            trimmed = passage.model_copy()
            if len(passage.text) > max_chars_per_passage:
                trimmed.text = passage.text[:max_chars_per_passage]
            selected.append(trimmed)
            used_tokens += cost
    return selected or passages[:1]


def trim_history_turns(history: List[ConversationTurn], *, max_turns: int = 6, max_tokens: int = 600) -> List[ConversationTurn]:
    turns = [t for t in history if t.content][-max_turns:]
    while turns and sum(estimate_tokens(t.content) for t in turns) > max_tokens:
        turns = turns[1:]
    return turns