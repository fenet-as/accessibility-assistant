"""Learner-facing bilingual copy shared by the web, Telegram and SMS channels."""

from typing import Dict

from assistant.domain.models import HUMAN_HELP_ACTION, ChatResponse, ChatStatus

NOT_FOUND: Dict[str, str] = {
    "en": (
        "I'm sorry, but this question cannot be answered from the available course material. "
        "Would you like to connect with a human tutor?"
    ),
    "am": "ይቅርታ፣ ይህ ጥያቄ በተሰጠው የትምህርት ይዘት ውስጥ አልተገኘም። ከቀጥታ ረዳት/መምህር ጋር መገናኘት ይፈልጋሉ?",
}

ESCALATION_CREATED: Dict[str, str] = {
    "en": "A live tutor has been notified. You can join the room below when ready to share your screen.",
    "am": "የቀጥታ መምህር ተነግሯል። ስክሪንዎን ለማጋራት ዝግጁ ሲሆኑ ከታች ያለውን ክፍል ይቀላቀሉ።",
}


def localized(messages: Dict[str, str], language: str) -> str:
    return messages.get(language, messages["en"])


def not_found_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.NOT_FOUND,
        language=language,
        answer=localized(NOT_FOUND, language),
        citations=[],
        actions=[HUMAN_HELP_ACTION],
    )
