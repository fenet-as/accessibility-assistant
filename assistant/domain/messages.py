"""Learner-facing copy shared by the web, Telegram and SMS channels (all six languages)."""

import re
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

OUT_OF_SCOPE: Dict[str, str] = {
    "en": (
        "I'm Savanna's learning assistant, so I focus on your course and on topics like virtual assistant "
        "work, freelancing, remote work, digital skills and careers. That question is outside what I can "
        "help with here. Feel free to ask me anything about those topics!"
    ),
    "am": (
        "እኔ የሳቫና የትምህርት ረዳት ነኝ፤ ትኩረቴ በትምህርትዎ እና እንደ ቨርቹዋል ረዳትነት፣ ፍሪላንሲንግ፣ የርቀት ሥራ፣ "
        "ዲጂታል ክህሎቶች እና ሙያ ባሉ ርዕሶች ላይ ነው። ይህ ጥያቄ ከዚህ ወሰን ውጭ ነው። ስለነዚህ ርዕሶች ማንኛውንም ጥያቄ ይጠይቁኝ!"
    ),
    "ti": (
        "ኣነ ናይ ሳቫና ትምህርቲ ሓጋዚ እየ፤ ኣቓልቦይ ኣብ ትምህርትኻን ከም ቨርቹዋል ኣሲስታንት ስራሕ፣ ፍሪላንሲንግ፣ "
        "ካብ ርሑቕ ምስራሕ፣ ዲጂታላዊ ክእለትን ሞያን ዝኣመሰሉ ኣርእስታትን እዩ። እዚ ሕቶ ካብዚ ወሰን ወጻኢ እዩ። "
        "ብዛዕባ እዞም ኣርእስታት ዝኾነ ሕቶ ሕተተኒ!"
    ),
    "om": (
        "Ani gargaaraa barnootaa Savanna ti; xiyyeeffannaan koo barnoota keessan fi mata dureewwan akka hojii "
        "gargaaraa virtuaalaa, hojii dhuunfaa (freelancing), hojii fagoo irraa, dandeettii dijitaalaa fi "
        "hojii irratti. Gaaffiin kun daangaa kanaan ala. Mata dureewwan kanneen irratti gaaffii kamiyyuu na gaafadhu!"
    ),
    "so": (
        "Waxaan ahay kaaliyaha waxbarashada Savanna; diiradaydu waa koorsadaada iyo mawduucyada sida shaqada "
        "kaaliyaha casriga ah (VA), freelancing, shaqada fogaan, xirfadaha dijitaalka ah iyo xirfad-shaqo. "
        "Su'aashani waa ka baxsan waxa aan halkan kaaga caawin karo. Wax kasta oo ku saabsan mawduucyadaas i weydii!"
    ),
    "ar": (
        "أنا مساعد التعلّم في Savanna، وأركّز على دورتك وعلى مواضيع مثل عمل المساعد الافتراضي والعمل الحر "
        "والعمل عن بُعد والمهارات الرقمية والمسار المهني. هذا السؤال خارج نطاق ما يمكنني المساعدة فيه هنا. "
        "اسألني عن أي شيء في هذه المواضيع!"
    ),
}

OFFLINE_GENERAL_UNAVAILABLE: Dict[str, str] = {
    "en": (
        "That question needs cloud AI or a saved answer, which are not available offline. "
        "I can still search your downloaded course pack for lesson content, or you can ask again when you are online."
    ),
    "am": (
        "ይህ ጥያቄ የደመና AI ወይም የተቀመጠ መልስ ይፈልጋል፤ ኦፍላይን አይገኙም። "
        "የወረደውን የትምህርት ጥቅል መፈለግ እችላለሁ፣ ወይም ሲገናኙ እንደገና ይጠይቁ።"
    ),
    "ti": (
        "እዚ ሕቶ ናይ ደመና AI ወይ ዝተቐመጠ መልሲ የድሊ፤ ኦፍላይን ኣይርከብን። "
        "ዝወረደ ትሕዝቶ ትምህርቲ ክድልይ፣ ወይ ምስ ተራኸብካ ደጊምካ ሕተት።"
    ),
    "om": (
        "Gaaffiin kun AI duumessaa ykn deebii kuufame barbaada; toora alaa hin argamu. "
        "Paakii barnootaa buufame barbaaduun nan danda'a, ykn yeroo online taatu irra deebi'ii gaafadhu."
    ),
    "so": (
        "Su'aashani waxay u baahan tahay AI daruureed ama jawaab la keydiyay; offline lama heli karo. "
        "Weli waan ka raadin karaa xirmada casharka ee la soo dejiyay, ama markaad online noqoto dib u weydii."
    ),
    "ar": (
        "هذا السؤال يحتاج إلى ذكاء اصطناعي سحابي أو إجابة محفوظة، وهما غير متاحين دون اتصال. "
        "ما زال بإمكاني البحث في حزمة الدورة المُنزَّلة، أو أعد السؤال عند الاتصال."
    ),
}

UNCLEAR_REFERENCE: Dict[str, str] = {
    "en": "I'm not sure what you are referring to. Could you tell me which topic you mean?",
    "am": "ምን እንደሚያመለክቱ እርግጠኛ አይደለሁም። የትኛውን ርዕስ ማለትዎ እንደሆነ ሊነግሩኝ ይችላሉ?",
    "ti": "እንታይ ከም እተመልክት ኣይርግጸንን። ኣየናይ ኣርእስቲ ማለትካ ምዃኑ ክትነግረኒ ትኽእልዶ?",
    "om": "Maal akka agarsiiftu hin mirkaneeffanne. Mata duree kam akka jechuu barbaadde natti himuu dandeessaa?",
    "so": "Ma hubo waxa aad tilmaamayso. Ma ii sheegi kartaa mawduuca aad ula jeeddo?",
    "ar": "لست متأكدًا مما تشير إليه. هل يمكنك أن تخبرني بالموضوع الذي تقصده؟",
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
        answer_source="none",
        provider="none",
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


def out_of_scope_response(language: str, confidence: Optional[float] = None) -> ChatResponse:
    """Course-scope policy decline: the question is off-topic, not merely missing from the course."""
    return ChatResponse(
        status=ChatStatus.OUT_OF_SCOPE,
        language=language,
        answer=localized(OUT_OF_SCOPE, language),
        citations=[],
        actions=[],
        confidence=confidence,
        answer_source="none",
        provider="scope_policy",
    )


def unclear_reference_response(language: str, suggestions: List[str]) -> ChatResponse:
    """A pronoun or 'explain this' with nothing earlier in the conversation to refer to."""
    return ChatResponse(
        status=ChatStatus.NEEDS_CLARIFICATION,
        language=language,
        answer="\n".join([localized(UNCLEAR_REFERENCE, language)] + [f"- {s}" for s in suggestions]),
        citations=[],
        actions=[CLARIFY_ACTION, HUMAN_HELP_ACTION],
        suggestions=suggestions,
    )


COURSE_CHOICE: Dict[str, str] = {
    "en": (
        "I found more than one possible course for that name. "
        "Please choose the course you mean (you can keep the same question):"
    ),
    "am": "ከአንድ በላይ ተመሳሳይ የኮርስ ስም አግኝቻለሁ። እባክዎ የሚፈልጉትን ኮርስ ይምረጡ (ጥያቄዎን እንዳለ ማቆየት ይችላሉ)፦",
    "ti": "ካብ ሓደ ንላዕሊ ተመሳሳሊ ስም ኮርስ ረኺበ። በጃኹም ዝደለኹምዎ ኮርስ ምረጹ (ሕቶኹም ከም ዘሎ ክትሓልውዎ ትኽእሉ ኢኹም)፦",
    "om": "Maqaa koorsii tokkoo ol argadhe. Maaloo koorsii barbaaddu filadhu (gaaffii kee akka jirutti qabachuu dandeessa):",
    "so": "Waxaan helay in ka badan hal koors oo magacaas leh. Fadlan dooro koorsada aad ula jeedo (su'aasha waa la hayn karaa):",
    "ar": "وجدت أكثر من دورة محتملة لهذا الاسم. يُرجى اختيار الدورة المقصودة (يمكنك الإبقاء على السؤال كما هو):",
}


def course_choice_response(language: str, suggestions: List[str]) -> ChatResponse:
    """Ambiguous course-name match — ask the learner to pick a course."""
    return ChatResponse(
        status=ChatStatus.NEEDS_CLARIFICATION,
        language=language,
        answer="\n".join([localized(COURSE_CHOICE, language)] + [f"- {s}" for s in suggestions]),
        citations=[],
        actions=[CLARIFY_ACTION, HUMAN_HELP_ACTION],
        suggestions=suggestions,
        answer_source="none",
        provider="course_matcher",
        question_type="ambiguous",
    )


def translation_notice(language: str) -> str:
    return localized(TRANSLATION_UNAVAILABLE, language)


def welcome_message(language: str) -> str:
    return ui_string(language if language in TRANSLATION_UNAVAILABLE else "en", "welcome")


# ── Greeting / social message handling ───────────────────────────────────────

GREETING_PATTERNS: Dict[str, List[str]] = {
    "en": ["hi", "hello", "hey", "howdy", "good morning", "good afternoon", "good evening", "greetings", "sup", "what's up"],
    "am": [
        "ሰላም", "ሄሎ", "ጤና ይስጥልኝ", "እንደምን አደሩ", "እንደምን ነህ", "እንደምን ናችሁ",
        "እንዴት ነህ", "እንዴት ናችሁ", "ሰላም እንዴት", "ሰላም ነህ",
    ],
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


# If these appear, the learner is asking about course content — never treat as pure greeting.
# Course / academic intent — keep out of pure greetings like "ሰላም እንዴት ነህ".
_CONTENT_INTENT = re.compile(
    r"(?:^|[\s])(?:what|why|define|definition|explain|"
    r"virtual|assistant|\bva\b|course|lesson|type|types|categor|"
    r"ምን|ማለት|ስንት|ለምን|ቨርቹዋል|ረዳት|ትምህርት|"
    r"እንታይ|gaaffii|waa'?ee|maxaa)(?:$|[\s?.!])",
    re.IGNORECASE,
)


def _social_pattern_language(text: str, patterns: Dict[str, List[str]]) -> Optional[str]:
    """If the message is a short social phrase, return which language pattern matched."""
    import re as _re

    from assistant.domain.language import disambiguate_ethiopic

    lowered = text.strip().lower()
    words = lowered.split()
    if len(words) > 6:
        return None
    # Real course questions that happen to contain "hey" / "ሰላም" must not short-circuit.
    if len(words) > 2 and _CONTENT_INTENT.search(lowered):
        return None
    matches: List[str] = []
    for lang, phrases in patterns.items():
        for phrase in phrases:
            pattern = (
                r"(?<![a-zA-Z\u1200-\u137F\u0600-\u06FF])"
                + _re.escape(phrase.lower())
                + r"(?![a-zA-Z\u1200-\u137F\u0600-\u06FF])"
            )
            if _re.search(pattern, lowered):
                word_count = len(words)
                # Single-word greetings only when the message is very short (≤2 tokens).
                if len(phrase.split()) == 1 and word_count > 2:
                    continue
                matches.append(lang)
                break
    if not matches:
        return None
    return disambiguate_ethiopic(text, matches[0])


def greeting_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(GREETING_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
        provider="social",
        answer_source="social",
    )


def farewell_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(FAREWELL_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
        provider="social",
        answer_source="social",
    )


def thanks_response(language: str) -> ChatResponse:
    return ChatResponse(
        status=ChatStatus.ANSWERED,
        language=language,
        answer=localized(THANKS_REPLY, language),
        citations=[],
        actions=[],
        confidence=1.0,
        provider="social",
        answer_source="social",
    )


def _reply_language(message: str, detected: str, pattern_lang: Optional[str]) -> str:
    from assistant.domain.language import AUTO, LANGUAGES, disambiguate_ethiopic

    if detected in LANGUAGES and detected != AUTO:
        return detected
    if pattern_lang in LANGUAGES:
        return disambiguate_ethiopic(message, pattern_lang)
    return disambiguate_ethiopic(message, detected if detected in LANGUAGES else "am")


def detect_social_response(message: str, language: str) -> Optional[ChatResponse]:
    """
    If the message is a greeting, farewell, or thanks, return an appropriate
    ChatResponse immediately — bypassing BM25 retrieval entirely.
    Returns None if this is a real course question.
    """
    lang = _social_pattern_language(message, GREETING_PATTERNS)
    if lang:
        return greeting_response(_reply_language(message, language, lang))
    lang = _social_pattern_language(message, FAREWELL_PATTERNS)
    if lang:
        return farewell_response(_reply_language(message, language, lang))
    lang = _social_pattern_language(message, THANKS_PATTERNS)
    if lang:
        return thanks_response(_reply_language(message, language, lang))
    return None
