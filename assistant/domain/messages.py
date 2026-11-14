"""Learner-facing copy shared by the web, Telegram and SMS channels (all six languages)."""

from typing import Dict, List, Optional

from assistant.domain.language import ui_string
from assistant.domain.models import CLARIFY_ACTION, HUMAN_HELP_ACTION, ChatResponse, ChatStatus

NOT_FOUND: Dict[str, str] = {
    "en": (
        "I'm sorry, but this question cannot be answered from the available course material. "
        "Would you like to connect with a human tutor?"
    ),
    "am": "ይቅርታ፣ ይህ ጥያቄ በተሰጠው የትምህርት ይዘት ውስጥ አልተገኘም። ከቀጥታ ረዳት/መምህር ጋር መገናኘት ይፈልጋሉ?",
    "ti": "ይቕሬታ፣ እዚ ሕቶ ካብ ዘሎ ትሕዝቶ ትምህርቲ ክምለስ ኣይከኣለን። ምስ ሓያል መምህር ክትራኸብ ትደሊዶ?",
    "om": "Dhiifama, gaaffiin kun qabiyyee barnootaa jiru irraa deebii argachuu hin dandeenye. "
          "Barsiisaa waliin wal qunnamuu barbaaddaa?",
    "so": "Waan ka xumahay, su'aashan lagama jawaabi karo nuxurka casharka ee jira. "
          "Ma rabtaa inaad la xiriirto macallin?",
    "ar": "عذرًا، لا يمكن الإجابة عن هذا السؤال من محتوى الدورة المتاح. هل ترغب بالتواصل مع معلّم؟",
}

ESCALATION_CREATED: Dict[str, str] = {
    "en": "A live tutor has been notified. You can join the room below when ready to share your screen.",
    "am": "የቀጥታ መምህር ተነግሯል። ስክሪንዎን ለማጋራት ዝግጁ ሲሆኑ ከታች ያለውን ክፍል ይቀላቀሉ።",
    "ti": "ሓያል መምህር ተሓቢሩ። ስክሪንካ ንምክፋል ድሉው ምስኾንካ ኣብ ታሕቲ ዘሎ ክፍሊ ተጸንበር።",
    "om": "Barsiisaan yeroo dhugaa beekameera. Argii kee qooduuf qophii yoo taate kutaa armaan gadii seeni.",
    "so": "Macallin toos ah ayaa la ogeysiiyay. Markaad diyaar u tahay inaad shaashadda wadaagto, qolka hoose gal.",
    "ar": "تم إخطار معلّم مباشر. يمكنك الانضمام إلى الغرفة أدناه عندما تكون جاهزًا لمشاركة شاشتك.",
}

NEEDS_CLARIFICATION: Dict[str, str] = {
    "en": "I'm not sure which part of the course you mean. Could you rephrase, or pick one of these sections?",
    "am": "የትኛውን የትምህርቱን ክፍል እንደሚጠይቁ እርግጠኛ አይደለሁም። እባክዎ ጥያቄዎን በሌላ መንገድ ይጻፉ ወይም ከእነዚህ ክፍሎች አንዱን ይምረጡ።",
    "ti": "ናይ ትምህርቲ ክፋል እንታይ ከም እትሓትት ኣይርግጸንን። በጃኹም ሕቶኹም ብኻልእ መንገዲ ጸሓፉ ወይ ካብዚኣቶም ምረጹ።",
    "om": "Kutaa barnootaa kam akka gaafattu hin beeku. Maaloo gaaffii kee irra deebi'ii barreessi, ykn kutaa armaan gadii keessaa filadhu.",
    "so": "Ma hubo qaybta casharka ee aad ula jeedo. Fadlan dib u qor, ama dooro mid ka mid ah qaybahan.",
    "ar": "لست متأكدًا أي جزء من الدورة تقصد. هل يمكنك إعادة صياغة السؤال أو اختيار أحد هذه الأقسام؟",
}

TRANSLATION_UNAVAILABLE: Dict[str, str] = {
    "en": (
        "A curated translation for this section is not available in your selected language. "
        "Here is the original course text (citations unchanged):"
    ),
    "am": (
        "ለዚህ ክፍል በመረጡት ቋንቋ የተዘጋጀ ትርጉም የለም። "
        "የመጀመሪያው የትምህርት ጽሑፍ እንደዚህ ነው (ምንጮቹ አልተቀየሩም)፡"
    ),
    "ti": (
        "ንዚ ክፋል ብዝመረጽኩሞ ቋንቋ ዝተዳለወ ትርጉም የለን። "
        "ናይ ትምህርቲ ጽሑፍ ከምዚ እዩ (ምንጭታት ኣይተቐየሩን)፡"
    ),
    "om": (
        "Kutaa kanaaf afaan filatteetti hiikkaa qophii ta'e hin jiru. "
        "Barruun barnootaa jalqabaa kunotti (maddoonni hin jijjiiramne):"
    ),
    "so": (
        "Turjumaad diyaarsan oo ku saabsan qaybtan kuma jirto luqadda aad dooratay. "
        "Waa qoraalka asalka ah ee casharka (xigashooyinku isma beddelin):"
    ),
    "ar": (
        "لا تتوفر ترجمة معتمدة لهذا القسم باللغة التي اخترتها. "
        "إليك النص الأصلي من الدورة (المراجع لم تتغيّر):"
    ),
}


def localized(messages: Dict[str, str], language: str) -> str:
    return messages.get(language) or messages["en"]


def not_found_response(language: str, confidence: Optional[float] = None) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.NOT_FOUND,
        language=language,
        answer=localized(NOT_FOUND, language),
        citations=[],
        actions=[HUMAN_HELP_ACTION],
        confidence=confidence,
    )


def clarification_response(language: str, suggestions: List[str], confidence: Optional[float]) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.NEEDS_CLARIFICATION,
        language=language,
        answer="\n".join([localized(NEEDS_CLARIFICATION, language)] + [f"- {s}" for s in suggestions]),
        citations=[],
        actions=[CLARIFY_ACTION, HUMAN_HELP_ACTION],
        confidence=confidence,
        suggestions=suggestions,
    )


def translation_notice(language: str) -> str:
    return localized(TRANSLATION_UNAVAILABLE, language)


def welcome_message(language: str) -> str:
    return ui_string(language if language in TRANSLATION_UNAVAILABLE else "en", "welcome")
