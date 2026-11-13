"""
Grounding Engine & Conversation Coordinator.
Enforces strict anti-hallucination thresholds and citation linking.
"""

import re
from pathlib import Path
from typing import Optional
from assistant.core.models import (
    ChatRequest,
    ChatResponse,
    ChatStatus,
    Citation,
    AIProvider,
)
from assistant.core.retrieval import BM25Retriever
from assistant.core.providers.factory import get_ai_provider


class GroundingEngine:
    RELEVANCE_THRESHOLD = 0.35  # Threshold below which questions are rejected as not_found

    def __init__(self, chunks_path: Optional[Path] = None, provider: Optional[AIProvider] = None):
        if chunks_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            chunks_path = base_dir / "data" / "chunks.json"

        self.retriever = BM25Retriever(chunks_path)
        self._explicit_provider = provider

    @property
    def provider(self) -> AIProvider:
        if self._explicit_provider:
            return self._explicit_provider
        return get_ai_provider()

    def detect_language(self, text: str, requested_lang: str = "auto") -> str:
        """Detect language if 'auto', otherwise return requested language."""
        if requested_lang in ["am", "en"]:
            return requested_lang

        # Check for Ethiopic Unicode block (\u1200 - \u137F)
        if re.search(r"[\u1200-\u137F]", text):
            return "am"
        return "en"

    def process_query(self, request: ChatRequest) -> ChatResponse:
        """
        Main pipeline:
        1. Language detection
        2. Course retrieval
        3. Threshold confidence check (rejection rule)
        4. Grounded synthesis with citations
        """
        lang = self.detect_language(request.message, request.language)
        is_simple = (request.mode == "simple")

        # 1. Retrieve candidate passages
        passages = self.retriever.search(request.message, top_k=3)

        # 2. Rejection rule: If no passages or top score is below threshold
        if not passages or passages[0].score < self.RELEVANCE_THRESHOLD:
            if lang == "am":
                rejection_msg = "ይቅርታ፣ ይህ ጥያቄ በተሰጠው የትምህርት ይዘት ውስጥ አልተገኘም። ከቀጥታ ረዳት/መምህር ጋር መገናኘት ይፈልጋሉ?"
            else:
                rejection_msg = (
                    "I'm sorry, but this question cannot be answered from the available course material. "
                    "Would you like to connect with a human tutor?"
                )

            return ChatResponse(
                status=ChatStatus.NOT_FOUND,
                language=lang,
                answer=rejection_msg,
                citations=[],
                actions=["get_human_help"],
            )

        # 3. Grounded answer generation via pluggable provider
        response = self.provider.generate(
            question=request.message,
            passages=passages,
            language=lang,
            simple=is_simple,
        )

        return response

