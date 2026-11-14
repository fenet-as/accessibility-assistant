"""Offline provider: extractive answers from the top passage. No network, no cost."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from assistant.domain.messages import not_found_response
from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus, Passage

MIN_SENTENCE_LENGTH = 10
SENTENCES_NORMAL = 4
SENTENCES_SIMPLE = 2
MAX_CITATIONS = 2


def load_translations(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if not path or not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {lang: answers for lang, answers in data.items() if not lang.startswith("_")}


class OfflineFAQProvider:
    name: str = "offline_faq"

    def __init__(self, translations_path: Optional[Path] = None):
        self._translations = load_translations(translations_path)

    def generate(
        self,
        question: str,
        passages: List[Passage],
        language: str,
        simple: bool = False,
    ) -> ChatResponse:
        if not passages:
            return not_found_response(language)

        top = passages[0]
        summary = self._summarize(top.text, SENTENCES_SIMPLE if simple else SENTENCES_NORMAL)
        answer = self._translate(top, language) or (
            f"እንደ ትምህርቱ ይዘት፡ {top.section} - {summary}" if language == "am" else summary
        )

        return ChatResponse(
            status=ChatStatus.ANSWERED,
            language=language,
            answer=answer,
            citations=[p.to_citation() for p in passages[:MAX_CITATIONS]],
            actions=[HUMAN_HELP_ACTION],
        )

    @staticmethod
    def _summarize(text: str, max_sentences: int) -> str:
        sentences = [s.strip() for s in text.split(". ") if len(s.strip()) > MIN_SENTENCE_LENGTH]
        return ". ".join(sentences[:max_sentences]) + "."

    def _translate(self, passage: Passage, language: str) -> Optional[str]:
        for anchor_fragment, answer in self._translations.get(language, {}).items():
            if anchor_fragment in passage.anchor:
                return answer
        return None
