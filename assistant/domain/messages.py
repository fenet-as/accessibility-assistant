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


# ── Greeting / social message handling ───────────────────────────────────────

GREETING_PATTERNS: Dict[str, List[str]] = {
    "en": ["hi", "hello", "hey", "howdy", "good morning", "good afternoon", "good evening", "greetings", "sup", "what's up"],
    "am": ["ሰላም", "ሄሎ", "ጤና ይስጥልኝ", "እንደምን አደሩ", "እንደምን ነህ", "እንደምን ናችሁ"],
    "ti": ["ሰላም", "ሄሎ", "ከመይ ኣለኻ", "ከመይ ሃሎ"],
    "om": ["nagaa", "akkam", "salaam", "asalaamaleykum"],
    "so": ["nabadgelyo", "nabad", "salaan", "asc", "assalamu calaykum"],
    "ar": ["مرحبا", "السلام عليكم", "أهلا", "هلا", "مرحباً"],
}

FAREWELL_PATTERNS: Dict[str, List[str]] = {
    "en": ["bye", "goodbye", "see you", "see ya", "cya", "later", "take care", "farewell", "good night", "ttyl"],
    "am": ["ቻው", "ሰላም ሁን", "በዳሜ", "እስኪ ልሄድ"],
    "ti": ["ሰላም ኩን", "ቻው"],
    "om": ["nagatti", "nagaya", "nagaan tura"],
    "so": ["nabadgelyo", "nabad", "mahadsanid"],
    "ar": ["مع السلامة", "وداعا", "إلى اللقاء", "باي"],
}

THANKS_PATTERNS: Dict[str, List[str]] = {
    "en": ["thanks", "thank you", "thx", "ty", "cheers", "appreciate", "much appreciated"],
    "am": ["አመሰግናለሁ", "ሞጋሽ", "ኣምስጋናሁ"],
    "ti": ["የቐንየለይ", "ብዙሕ የቐንየለይ"],
    "om": ["galatoomaa", "baay'ee galatoomaa"],
    "so": ["mahadsanid", "aad ayaad u mahadsan tahay"],
    "ar": ["شكراً", "شكرا", "ممنون", "جزاك الله خيرا"],
}

GREETING_REPLY: Dict[str, str] = {
    "en": "Hello! 👋 I'm your Savanna learning assistant. Ask me anything about your VA course — lessons, concepts, or career tips!",
    "am": "ሰላም! 👋 እኔ የሳቫና ትምህርት ረዳትዎ ነኝ። ስለ ቨርቹዋል ረዳትነት ትምህርቶ ማንኛውንም ጥያቄ ይጠይቁኝ!",
    "ti": "ሰላም! 👋 ናይ ሳቫና ትምህርቲ ሓጋዚኻ እየ። ብዛዕባ ቨርቹዋል ኣሲስታንት ትምህርቲ ዝኾነ ሕቶ ሕተተኒ!",
    "om": "Nagaa! 👋 Ani gargaaraa barnootaa Savanna kee nan ta'a. Barnootaa VA kee irratti gaaffii kamiyyuu naaf gaafadhu!",
    "so": "Nabad! 👋 Waxaan ahay kaaliyahaaga waxbarashada Savanna. Wax kasta oo ku saabsan koorsadaada VA ah iga weydii!",
    "ar": "مرحباً! 👋 أنا مساعدك التعليمي في Savanna. اسألني عن أي شيء يتعلق بدورتك في المساعدة الافتراضية!",
}

FAREWELL_REPLY: Dict[str, str] = {
    "en": "Goodbye! 👋 Good luck with your studies. Come back anytime you have questions!",
    "am": "ቻው! 👋 ትምህርትዎ ይሳካ። ጥያቄ ሲኖርዎ ወደ እኛ ይመለሱ!",
    "ti": "ቻው! 👋 ትምህርትኻ ይሰልጥ። ሕቶ ምስ ሃለዉካ ተመለስ!",
    "om": "Nagatti! 👋 Barnoochiif milkaa'ina haa argattan. Gaaffii yoo qabdan deebi'aa!",
    "so": "Nabadgelyo! 👋 Barashaada ugu barakayso. Mar kasta oo su'aal qabto ku soo noqo!",
    "ar": "مع السلامة! 👋 بالتوفيق في دراستك. عُد في أي وقت لديك أسئلة!",
}

THANKS_REPLY: Dict[str, str] = {
    "en": "You're welcome! 😊 Let me know if you have any more questions about the course.",
    "am": "እባክዎ! 😊 ሌላ ጥያቄ ካለዎ ያሳውቁኝ።",
    "ti": "ብዘይ ምስጋና! 😊 ካልእ ሕቶ ምስ ሃለዉካ ሓብረኒ።",
    "om": "Dheebuu! 😊 Gaaffii biroo yoo qabdan naaf beeksisi.",
    "so": "Adigaa mudan! 😊 Su'aal kale haddaad qabto i ogeysii.",
    "ar": "على الرحب والسعة! 😊 أخبرني إن كان لديك المزيد من الأسئلة حول الدورة.",
}


def _matches_patterns(text: str, patterns: Dict[str, List[str]]) -> bool:
    """Return True if the text (whole message, lowercased) is a social phrase.
    Uses whole-word matching to prevent false positives (e.g. 'tyre' vs 'ty').
    Only triggers when the entire message is essentially a social phrase,
    not when it's embedded in a longer question.
    """
    lowered = text.strip().lower()
    # Only intercept short messages (<=6 words) to avoid swallowing real questions
    word_count = len(lowered.split())
    if word_count > 6:
        return False
    import re
    for _, phrases in patterns.items():
        for phrase in phrases:
            # Whole-phrase match at word boundaries
            pattern = r"(?<![a-zA-Z\u1200-\u137F\u0600-\u06FF])" + re.escape(phrase) + r"(?![a-zA-Z\u1200-\u137F\u0600-\u06FF])"
            if re.search(pattern, lowered):
                return True
    return False


def greeting_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(GREETING_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
    )


def farewell_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(FAREWELL_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
    )


def thanks_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(THANKS_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
    )


def detect_social_response(message: str, language: str) -> Optional[ChatResponse]:
    """
    If the message is a greeting, farewell, or thanks, return an appropriate
    ChatResponse immediately — bypassing BM25 retrieval entirely.
    Returns None if this is a real course question.
    """
    if _matches_patterns(message, GREETING_PATTERNS):
        return greeting_response(language)
    if _matches_patterns(message, FAREWELL_PATTERNS):
        return farewell_response(language)
    if _matches_patterns(message, THANKS_PATTERNS):
        return thanks_response(language)
    return None
