"""Offline provider: extractive answers built only from retrieved passages. No network, no cost.

Answers in the learner's language come from curated ``translations`` on each chunk/passage.
If none exist, the original course text is returned with a clear notice — translations are
never invented offline, and no cloud translation API is called.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from assistant.domain.messages import not_found_response, translation_notice
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, ConversationTurn, Passage
from assistant.infrastructure.text_analysis import analyze, synonyms_of

MIN_SENTENCE_LENGTH = 10
SENTENCES_NORMAL = 6
SENTENCES_SIMPLE = 2
SENTENCES_SUPPORTING = 2
MAX_PASSAGES = 3
SENTENCE_SPLIT = re.compile(r"(?<=[.!?።؟])\s+")


def load_translations(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Load optional legacy JSON, else the embedded curated translation map."""
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {lang: answers for lang, answers in data.items() if not lang.startswith("_")}
    try:
        from assistant.data.curated_translations import CURATED_TRANSLATIONS

        return {lang: dict(answers) for lang, answers in CURATED_TRANSLATIONS.items()}
    except ImportError:
        return {}


def best_sentences(text: str, query_terms: Set[str], limit: int) -> str:
    """The `limit` sentences sharing most terms with the question, kept in reading order."""
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if len(s.strip()) > MIN_SENTENCE_LENGTH]
    if not sentences:
        return text.strip()
    if len(sentences) <= limit:
        return text.strip()
    ranked = sorted(range(len(sentences)),
                    key=lambda i: (-len(query_terms & set(analyze(sentences[i]))), i))
    chosen = sorted(ranked[:limit])
    return " ".join(sentences[i] for i in chosen)


class OfflineFAQProvider:
    name: str = "offline_faq"

    def __init__(self, translations_path: Optional[Path] = None):
        # Always have embedded curated translations available for offline languages.
        self._translations = load_translations(translations_path)

    def provider_status(self) -> dict:
        return {
            "name": self.name,
            "available": True,
            "status": "ready",
            "mode": "offline_extractive",
        }

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
        history: Optional[List[ConversationTurn]] = None,
        *,
        confidence: float = 0.0,
        answer_mode: str = "course",
        scope_confirmed: bool = True,
    ) -> ChatResponse:
        # Offline FAQ can only extract from passages; general-knowledge mode has nothing local to quote.
        if not passages:
            return not_found_response(language)

        used = self._passages_to_use(passages)
        # Score sentences against the CURRENT question only. Prior-turn terms used to leak
        # into extractive selection and could pull sentences from the wrong topic when
        # several passages were retrieved after a conversation turn.
        query_terms = set(analyze(question))
        for t in list(query_terms):
            query_terms.update(synonyms_of(t))
        _ = history  # history is unused for extractive FAQ; passages are already scoped.

        parts: List[str] = []
        used_fallback = False
        for position, passage in enumerate(used):
            limit = (SENTENCES_SIMPLE if simple else SENTENCES_NORMAL) if position == 0 else SENTENCES_SUPPORTING
            text, fell_back = self._render(passage, language, query_terms, limit)
            parts.append(text)
            used_fallback = used_fallback or fell_back

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer="\n\n".join(parts),
            citations=[p.to_citation() for p in used],
            actions=[HUMAN_HELP_ACTION],
            translation_fallback=used_fallback,
            provider=self.name,
            answer_source="faq",
        )

    @staticmethod
    def _passages_to_use(passages: List[Passage]) -> List[Passage]:
        """The top passage, plus any other passage that covers question terms the top one lacks."""
        used = [passages[0]]
        covered = set(passages[0].matched_terms)
        for passage in passages[1:MAX_PASSAGES]:
            new_terms = set(passage.matched_terms) - covered
            if new_terms:
                used.append(passage)
                covered |= new_terms
        return used

    def _render(self, passage: Passage, language: str, query_terms: Set[str], limit: int) -> Tuple[str, bool]:
        if language == "en":
            return best_sentences(passage.text, query_terms, limit), False

        # Prefer translations stored on the chunk itself (from chunks.json / SQLite).
        translated = passage.translations.get(language) or self._legacy_translation(passage, language)
        if translated:
            return translated, False

        # Never invent a translation offline: show the original course text and say so.
        summary = best_sentences(passage.text, query_terms, limit)
        return f"{translation_notice(language)}\n{summary}", True

    def _legacy_translation(self, passage: Passage, language: str) -> Optional[str]:
        """Optional legacy map (empty unless an old faq_translations file is still configured)."""
        for anchor_fragment, answer in self._translations.get(language, {}).items():
            if anchor_fragment and anchor_fragment in (passage.anchor or ""):
                return answer
        return None
