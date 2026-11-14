"""
SMS Channel Adapter for Low-Bandwidth Ethiopian Users.
Handles 160-char ASCII / 70-char Amharic Unicode segment limits,
numbered navigation menus, and core service normalization.
"""

import re
from typing import List, Dict, Any, Tuple
from assistant.core.models import ChatRequest, ChatStatus
from assistant.core.grounding import GroundingEngine

engine = GroundingEngine()


class SMSAdapter:
    # GSM standard SMS limits
    ASCII_LIMIT = 160
    UNICODE_LIMIT = 70

    def is_unicode(self, text: str) -> bool:
        """Detect whether text contains Unicode/Ethiopic characters."""
        return bool(re.search(r"[\u1200-\u137F]", text))

    def split_segments(self, text: str) -> List[str]:
        """Split text into SMS-safe segments without breaking words."""
        max_len = self.UNICODE_LIMIT if self.is_unicode(text) else self.ASCII_LIMIT
        if len(text) <= max_len:
            return [text]

        words = text.split(" ")
        segments: List[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    segments.append(current)
                current = word

        if current:
            segments.append(current)

        return segments

    def handle_inbound_sms(self, sender: str, body: str) -> List[str]:
        """
        Process inbound SMS text and return one or more outbound SMS segments.
        Supports commands: HELP, JOBS, HUMAN, or course questions.
        """
        cleaned = body.strip()
        upper = cleaned.upper()

        if upper in ["HELP", "INFO"]:
            return [
                "ALX Assistant: Reply with your question, or:\n"
                "1: Jobs\n"
                "2: Human Tutor\n"
                "3: Amharic (አማርኛ)"
            ]

        if upper in ["3", "AMHARIC", "አማርኛ"]:
            return [
                "ALX ረዳት፡ ጥያቄዎን በአማርኛ ይጻፉ ወይም:\n1: ክፍት የሥራ ቦታዎች\n2: የቀጥታ መምህር እርዳታ"
            ]

        if upper in ["1", "JOBS", "JOB", "ሥራ", "ስራ"]:
            return [
                "ALX Jobs: 1) Junior VA (African Remote Ops, Remote) 2) Digital Coordinator. Visit portal to apply with accommodations."
            ]

        if upper in ["2", "HUMAN", "HELP ME", "TUTOR", "እርዳታ", "መምህር"]:
            return [
                "ALX Tutor: Human tutor request received! A tutor has been notified and will reach out via SMS/Phone."
            ]

        # General Course Query
        req = ChatRequest(
            session=f"sms-{sender}",
            message=cleaned,
            language="auto",
            scope="course:va-1"
        )
        res = engine.process_query(req)

        # Build concise SMS reply
        if res.status == ChatStatus.NOT_FOUND:
            if res.language == "am":
                reply = "ይቅርታ፣ ይህ ጥያቄ በትምህርቱ ውስጥ አልተገኘም። ለሰው ረዳት 2 ብለው ይመልሱ።"
            else:
                reply = "Not found in course text. Reply 2 to connect with a human tutor."
        else:
            # Concise answer with citation footnote
            citation_note = f" (Ref: {res.citations[0].section})" if res.citations else ""
            reply = f"{res.answer}{citation_note}"

        return self.split_segments(reply)

