"""Centralized multilingual configuration for the six supported learner languages.

Detection combines script signals (Ethiopic, Arabic, Latin) with distinctive marker
words, so languages that share a script (Amharic/Tigrinya, English/Oromo/Somali)
are not decided by Unicode ranges alone. An explicit UI choice always wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SUPPORTED_LANGUAGES: Tuple[str, ...] = ("en", "am", "ti", "om", "so", "ar")
AUTO = "auto"

ETHIOPIC_PATTERN = re.compile(r"[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF]")
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_PATTERN = re.compile(r"[A-Za-zÀ-öø-ÿ]")
WORD_PATTERN = re.compile(r"[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF]+|[\u0600-\u06FF]+|[A-Za-zÀ-öø-ÿ']+")


@dataclass(frozen=True)
class LanguageSpec:
    code: str
    name_en: str
    name_native: str
    script: str  # ethiopic | arabic | latin
    direction: str  # ltr | rtl
    speech_recognition: str  # BCP-47 tag browsers usually accept
    speech_synthesis: str
    markers: Tuple[str, ...] = ()


LANGUAGES: Dict[str, LanguageSpec] = {
    "en": LanguageSpec(
        "en", "English", "English", "latin", "ltr", "en-US", "en-US",
        markers=("the", "what", "how", "why", "when", "where", "which", "virtual", "assistant",
                 "course", "lesson", "please", "explain", "about", "future", "client"),
    ),
    "am": LanguageSpec(
        "am", "Amharic", "አማርኛ", "ethiopic", "ltr", "am-ET", "am-ET",
        markers=("ነው", "ናቸው", "ምን", "እንዴት", "ማን", "የት", "ለምን", "ቨርቹዋል", "ረዳት",
                 "ሥራ", "ስራ", "ደንበኛ", "ትምህርት", "እባክዎ", "ይህ", "አለው"),
    ),
    "ti": LanguageSpec(
        "ti", "Tigrinya", "ትግርኛ", "ethiopic", "ltr", "ti-ET", "ti-ET",
        markers=("እንታይ", "ከመይ", "ዘሎ", "እዩ", "እየን", "ስራሕ", "መማሃርቲ", "ሓጋዚ",
                 "ደንበኛ", "ክእለት", "በጃኹም", "እዚ", "ወደፊት", "ትግርኛ"),
    ),
    "om": LanguageSpec(
        "om", "Afaan Oromo", "Afaan Oromo", "latin", "ltr", "om-ET", "om-ET",
        markers=("maal", "akkam", "jira", "jirti", "barnoota", "gargaarsa", "hojii", "dhaabbata",
                 "dhaamsa", "maalif", "eenyu", "eessa", "fayyadamuu", "barachuu", "oromoo", "afaan"),
    ),
    "so": LanguageSpec(
        "so", "Somali", "Soomaali", "latin", "ltr", "so-SO", "so-SO",
        markers=("waa", "maxay", "sidee", "maxaa", "yaa", "xaggee", "caawimaad", "caawimaadda", "shaqo",
                 "macmiil", "macallin", "fadlan", "waxaan", "tahay", "soomaali", "barashada", "kuwaas"),
    ),
    "ar": LanguageSpec(
        "ar", "Arabic", "العربية", "arabic", "rtl", "ar-SA", "ar-SA",
        markers=("ما", "كيف", "هل", "ماذا", "لماذا", "أين", "مساعد", "افتراضي", "عمل",
                 "دورة", "درس", "من فضلك", "مستقبل", "عميل", "مهارة", "الذكاء"),
    ),
}

# UI chrome: every string the widget or channels show outside the grounded answer.
UI_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "launcher": "Ask Tutor",
        "launcher_aria": "Ask Tutor - AI Learning Assistant",
        "header": "ALX Learning Assistant",
        "language": "Language",
        "language_aria": "Select response language",
        "auto": "Auto-detect",
        "simple_mode": "Simple Mode",
        "human_help": "Live Human Help",
        "human_help_aria": "Live Human Help - Request human tutor help",
        "close_aria": "Close Assistant",
        "placeholder": "Ask a question about this lesson...",
        "listening": "Listening... Speak your question now",
        "send": "Send",
        "send_aria": "Send message",
        "voice_aria": "Voice input - Speak your question",
        "voice_stop_aria": "Stop listening - Microphone active",
        "voice_unsupported": "Voice input is not available in this browser",
        "listen": "Listen",
        "listen_aria": "Listen - Read response aloud",
        "stop": "Stop",
        "stop_aria": "Stop - Stop reading aloud",
        "speak_unsupported": "Read-aloud is not available for this language on this device",
        "loading": "Searching course material...",
        "offline_error": "Unable to reach the assistant server. You can connect with a live human helper using the button above.",
        "welcome": "Hello! I am your course assistant. Ask me questions about this lesson. All answers are strictly grounded in course content.",
        "citations": "Course Citations:",
        "citation_aria": "Go to course source",
        "escalate_confirm": "Would you like to connect with a live tutor? A secure Jitsi meeting link will be created for you to share your screen with explicit consent.",
        "escalate_ok": "Human tutor request dispatched ({ticket})! When you are ready to share your screen, open the secure session: {url}",
        "escalate_fail": "Sorry, the help request could not be sent. Please try again.",
        "input_label": "Type your question",
        "detected": "Detected language",
    },
    "am": {
        "launcher": "ረዳት ጠይቅ",
        "launcher_aria": "ረዳት ጠይቅ - የትምህርት ረዳት",
        "header": "የALX የትምህርት ረዳት",
        "language": "ቋንቋ",
        "language_aria": "የመልስ ቋንቋ ይምረጡ",
        "auto": "በራስ መለየት",
        "simple_mode": "ቀላል ሁነታ",
        "human_help": "የቀጥታ ረዳት",
        "human_help_aria": "የቀጥታ ረዳት - ከሰው መምህር ጋር ይገናኙ",
        "close_aria": "ረዳቱን ዝጋ",
        "placeholder": "ስለዚህ ትምህርት ጥያቄዎን ይጠይቁ...",
        "listening": "እያዳመጠ ነው... አሁን ይናገሩ",
        "send": "ላክ",
        "send_aria": "መልእክት ላክ",
        "voice_aria": "የድምጽ ግቤት - ጥያቄዎን ይናገሩ",
        "voice_stop_aria": "ማዳመጥ አቁም - ማይክሮፎን ንቁ ነው",
        "voice_unsupported": "የድምጽ ግቤት በዚህ አሳሽ አይገኝም",
        "listen": "አዳምጥ",
        "listen_aria": "አዳምጥ - መልሱን በድምጽ ያንብቡ",
        "stop": "አቁም",
        "stop_aria": "አቁም - ማንበብ አቁም",
        "speak_unsupported": "በዚህ መሣሪያ ለዚህ ቋንቋ ማንበብ አይገኝም",
        "loading": "መልስ እየተፈለገ ነው...",
        "offline_error": "ይቅርታ፣ ከአገልጋዩ ጋር መገናኘት አልተቻለም። እባክዎ የቀጥታ ረዳትን ያነጋግሩ ወይም እንደገና ይሞክሩ።",
        "welcome": "ሰላም! እኔ የትምህርት ረዳትዎ ነኝ። ስለዚህ ትምህርት ጥያቄዎችን ይጠይቁ። መልሶች ከትምህርቱ ይዘት ብቻ ናቸው።",
        "citations": "የተጠቀሱ ምንጮች:",
        "citation_aria": "ወደ ትምህርቱ ምንጭ ሂድ",
        "escalate_confirm": "የቀጥታ ረዳት እርዳታ ይፈልጋሉ? ረዳቱን ወደ Jitsi ስክሪን መጋሪያ ክፍል ለመጋበዝ ፈቃደኛ ነዎት?",
        "escalate_ok": "የእርዳታ ጥያቄዎ ተልኳል ({ticket})! ከረዳቱ ጋር ለመነጋገር እና ስክሪንዎን ለማጋራት የሚከተለውን ሊንክ ይክፈቱ፡ {url}",
        "escalate_fail": "ይቅርታ፣ የእርዳታ ጥያቄውን መላክ አልተቻለም። እባክዎ እንደገና ይሞክሩ።",
        "input_label": "ጥያቄዎን ይጻፉ",
        "detected": "የተለየ ቋንቋ",
    },
    "ti": {
        "launcher": "ሓጋዚ ሕተት",
        "launcher_aria": "ሓጋዚ ሕተት - ናይ ትምህርቲ ሓጋዚ",
        "header": "ናይ ALX ትምህርቲ ሓጋዚ",
        "language": "ቋንቋ",
        "language_aria": "ቋንቋ መልሲ ምረጽ",
        "auto": "ብባዕሉ ምልላይ",
        "simple_mode": "ቀሊል ሞድ",
        "human_help": "ሓያል ሰብ ሓጋዚ",
        "human_help_aria": "ሓያል ሰብ ሓጋዚ - ምስ መምህር ተራኸብ",
        "close_aria": "ሓጋዚ ዕጸው",
        "placeholder": "ብዛዕባ እዚ ትምህርቲ ሕቶኻ ሕተት...",
        "listening": "ይሰምዕ ኣሎ... ሕጂ ተዛረብ",
        "send": "ላእክ",
        "send_aria": "መልእኽቲ ላእክ",
        "voice_aria": "ድምጺ ምእታው - ሕቶኻ ተዛረብ",
        "voice_stop_aria": "ምስማዕ ኣቁም",
        "voice_unsupported": "ድምጺ ምእታው ኣብዚ ብራውዘር የለን",
        "listen": "ሰምዕ",
        "listen_aria": "ሰምዕ - መልሲ ብድምጺ ኣንብብ",
        "stop": "ኣቁም",
        "stop_aria": "ኣቁም",
        "speak_unsupported": "ንዚ ቋንቋ ኣብዚ መሳርሒ ምንባብ የለን",
        "loading": "መልሲ ይድለ ኣሎ...",
        "offline_error": "ምስ ሰርቨር ክትራኸብ ኣይተኻእለን። በጃኹም ሓያል ሰብ ሓጋዚ ተጠቐሙ።",
        "welcome": "ሰላም! ኣነ ናይ ትምህርቲ ሓጋዝኻ እየ። ብዛዕባ እዚ ትምህርቲ ሕቶታት ሕተት። መልስታት ካብ ትሕዝቶ ትምህርቲ ጥራይ እዮም።",
        "citations": "ምንጭታት:",
        "citation_aria": "ናብ ምንጭ ትምህርቲ ኺድ",
        "escalate_confirm": "ምስ ሓያል መምህር ክትራኸብ ትደሊዶ? ናይ Jitsi ኣገናኽ ክፍጠር እዩ።",
        "escalate_ok": "ሕቶ ሓገዝ ተላኢኹ ({ticket})! ስክሪንካ ንምክፋል እዚ ሊንክ ክፈት፡ {url}",
        "escalate_fail": "ይቕሬታ፣ ሕቶ ሓገዝ ክለኣኽ ኣይከኣለን። ደጊምካ ፈትን።",
        "input_label": "ሕቶኻ ጸሓፍ",
        "detected": "ዝተለለየ ቋንቋ",
    },
    "om": {
        "launcher": "Gargaaraa Gaafadhu",
        "launcher_aria": "Gargaaraa Gaafadhu - Gargaaraa barnootaa",
        "header": "Gargaaraa Barnootaa ALX",
        "language": "Afaan",
        "language_aria": "Afaan deebii filadhu",
        "auto": "Ofumaan adda baasi",
        "simple_mode": "Haala salphaa",
        "human_help": "Gargaarsa Namaa",
        "human_help_aria": "Gargaarsa Namaa - Barsiisaan wal qunnami",
        "close_aria": "Gargaaraa cufi",
        "placeholder": "Waa'ee barnoota kanaa gaaffii kee gaafadhu...",
        "listening": "Dhaggeeffachaa jira... Amma dubbadhu",
        "send": "Ergi",
        "send_aria": "Ergaa ergi",
        "voice_aria": "Galtee sagalee - Gaaffii kee dubbadhu",
        "voice_stop_aria": "Dhaggeeffachuu dhaabi",
        "voice_unsupported": "Galtee sagalee browzera kana irratti hin jiru",
        "listen": "Dhaggeeffadhu",
        "listen_aria": "Dhaggeeffadhu - Deebii sagaleen dubbisi",
        "stop": "Dhaabi",
        "stop_aria": "Dhaabi",
        "speak_unsupported": "Afaan kanaaf meeshaa kana irratti dubbisuu hin jiru",
        "loading": "Deebii barbaadaa jira...",
        "offline_error": "Serverii waliin wal qunnamiin hin dandeenye. Gargaarsa namaa fayyadami.",
        "welcome": "Akkam! Ani gargaaraa barnootaa keeti. Waa'ee barnoota kanaa gaaffii gaafadhu. Deebiin qofa qabiyyee barnootaa irraa dhufa.",
        "citations": "Maddaalee:",
        "citation_aria": "Gara madda barnootaatti deemi",
        "escalate_confirm": "Barsiisaa waliin wal qunnamuu barbaaddaa? Linkii Jitsi ni uumama.",
        "escalate_ok": "Gaaffiin gargaarsaa ergame ({ticket})! Argii kee qooduuf linkii kana bani: {url}",
        "escalate_fail": "Dhiifama, gaaffiin gargaarsaa erguu hin dandeenye. Irra deebi'ii yaali.",
        "input_label": "Gaaffii kee barreessi",
        "detected": "Afaan adda ba'e",
    },
    "so": {
        "launcher": "Weeydii Macallinka",
        "launcher_aria": "Weeydii Macallinka - Caawimaadda waxbarashada",
        "header": "Caawiyaha Waxbarashada ALX",
        "language": "Luqadda",
        "language_aria": "Dooro luqadda jawaabta",
        "auto": "Si toos ah u ogow",
        "simple_mode": "Hab fudud",
        "human_help": "Caawimaad Bini'aadam",
        "human_help_aria": "Caawimaad Bini'aadam - La xiriir macallin",
        "close_aria": "Xir caawiyaha",
        "placeholder": "Weydii su'aal ku saabsan casharkan...",
        "listening": "Waa dhagaysanayaa... Hadda hadal",
        "send": "Dir",
        "send_aria": "Dir fariinta",
        "voice_aria": "Gelinta codka - Ku hadal su'aashaada",
        "voice_stop_aria": "Jooji dhageysiga",
        "voice_unsupported": "Gelinta codka kuma jirto browser-kan",
        "listen": "Dhageyso",
        "listen_aria": "Dhageyso - Akhri jawaabta cod ahaan",
        "stop": "Jooji",
        "stop_aria": "Jooji",
        "speak_unsupported": "Akhinta ma heli karo luqaddan qalabkan",
        "loading": "Waa raadinta waxyaabaha casharka...",
        "offline_error": "Lama gaadhi karo server-ka. Isticmaal caawimaadda bini'aadamka.",
        "welcome": "Salaan! Waxaan ahay caawiyahaaga casharka. Weydii su'aalo ku saabsan casharkan. Jawaabuhu waxay ka yimaadaan oo keliya nuxurka casharka.",
        "citations": "Xigashooyinka:",
        "citation_aria": "Tag isha casharka",
        "escalate_confirm": "Ma rabtaa inaad la xiriirto macallin? Xiriir Jitsi ayaa la abuuri doonaa.",
        "escalate_ok": "Codsiga caawimaadda waa la diray ({ticket})! Fur xiriirkan si aad u wadaagto shaashadda: {url}",
        "escalate_fail": "Waan ka xumahay, codsiga lama diri karin. Fadlan isku day mar kale.",
        "input_label": "Qor su'aashaada",
        "detected": "Luqadda la ogaaday",
    },
    "ar": {
        "launcher": "اسأل المساعد",
        "launcher_aria": "اسأل المساعد - مساعد التعلّم",
        "header": "مساعد التعلّم ALX",
        "language": "اللغة",
        "language_aria": "اختر لغة الإجابة",
        "auto": "اكتشاف تلقائي",
        "simple_mode": "وضع مبسّط",
        "human_help": "مساعدة بشرية مباشرة",
        "human_help_aria": "مساعدة بشرية مباشرة - تواصل مع معلّم",
        "close_aria": "إغلاق المساعد",
        "placeholder": "اطرح سؤالاً عن هذا الدرس...",
        "listening": "جاري الاستماع... تحدّث الآن",
        "send": "إرسال",
        "send_aria": "إرسال الرسالة",
        "voice_aria": "إدخال صوتي - انطق سؤالك",
        "voice_stop_aria": "إيقاف الاستماع",
        "voice_unsupported": "الإدخال الصوتي غير متاح في هذا المتصفح",
        "listen": "استمع",
        "listen_aria": "استمع - اقرأ الإجابة بصوت عالٍ",
        "stop": "إيقاف",
        "stop_aria": "إيقاف القراءة",
        "speak_unsupported": "القراءة الصوتية غير متاحة لهذه اللغة على هذا الجهاز",
        "loading": "جاري البحث في محتوى الدورة...",
        "offline_error": "تعذّر الاتصال بالخادم. يمكنك طلب مساعدة بشرية من الزر أعلاه.",
        "welcome": "مرحبًا! أنا مساعد الدورة. اسألني عن هذا الدرس. تُستمدّ الإجابات فقط من محتوى الدورة.",
        "citations": "مراجع الدورة:",
        "citation_aria": "الانتقال إلى مصدر الدورة",
        "escalate_confirm": "هل تريد التواصل مع معلّم مباشر؟ سيتم إنشاء رابط Jitsi آمن لمشاركة شاشتك بموافقتك.",
        "escalate_ok": "تم إرسال طلب المساعدة ({ticket})! عند الاستعداد لمشاركة شاشتك افتح الجلسة: {url}",
        "escalate_fail": "عذرًا، تعذّر إرسال طلب المساعدة. يُرجى المحاولة مجددًا.",
        "input_label": "اكتب سؤالك",
        "detected": "اللغة المكتشفة",
    },
}


@dataclass
class LanguageDetection:
    code: str
    confidence: float
    overridden: bool = False
    signals: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "confidence": round(self.confidence, 3),
            "overridden": self.overridden,
            "signals": {k: round(v, 3) for k, v in self.signals.items()},
            "name": LANGUAGES[self.code].name_en,
            "native_name": LANGUAGES[self.code].name_native,
            "direction": LANGUAGES[self.code].direction,
            "script": LANGUAGES[self.code].script,
        }


def contains_ethiopic(text: str) -> bool:
    return bool(ETHIOPIC_PATTERN.search(text or ""))


def contains_arabic(text: str) -> bool:
    return bool(ARABIC_PATTERN.search(text or ""))


def get_language(code: str) -> LanguageSpec:
    return LANGUAGES[code if code in LANGUAGES else "en"]


def ui_string(language: str, key: str) -> str:
    pack = UI_STRINGS.get(language) or UI_STRINGS["en"]
    return pack.get(key, UI_STRINGS["en"].get(key, key))


def language_catalog() -> List[Dict[str, object]]:
    """Public description of every supported language for the widget and channels."""
    return [
        {
            "code": spec.code,
            "name": spec.name_en,
            "native_name": spec.name_native,
            "script": spec.script,
            "direction": spec.direction,
            "speech_recognition": spec.speech_recognition,
            "speech_synthesis": spec.speech_synthesis,
            "ui": UI_STRINGS[spec.code],
        }
        for spec in LANGUAGES.values()
    ]


def _script_scores(text: str) -> Dict[str, float]:
    ethiopic = len(ETHIOPIC_PATTERN.findall(text))
    arabic = len(ARABIC_PATTERN.findall(text))
    latin = len(LATIN_PATTERN.findall(text))
    total = ethiopic + arabic + latin
    if total == 0:
        return {"ethiopic": 0.0, "arabic": 0.0, "latin": 0.0}
    return {
        "ethiopic": ethiopic / total,
        "arabic": arabic / total,
        "latin": latin / total,
    }


def _marker_hits(words: Sequence[str], markers: Sequence[str]) -> float:
    """Count distinctive markers, including simple affix forms (caawimaadda ≈ caawimaad)."""
    if not words or not markers:
        return 0.0
    marker_list = [m.lower() for m in markers]
    unique = {w.lower() for w in words}

    def matches(word: str, marker: str) -> bool:
        return word == marker or (len(marker) >= 4 and (word.startswith(marker) or marker.startswith(word)))

    hits = sum(1 for word in unique if any(matches(word, marker) for marker in marker_list))
    return hits / max(len(unique), 1)


def detect_language_with_confidence(text: str, requested: str = AUTO) -> LanguageDetection:
    """Return the best language guess.

    An explicit supported code always wins (manual override). Otherwise script
    ratios and marker words are combined; confidence reflects how decisive that was.
    """
    requested = (requested or AUTO).strip().lower()
    if requested in LANGUAGES:
        return LanguageDetection(requested, 1.0, overridden=True, signals={"override": 1.0})

    text = text or ""
    words = WORD_PATTERN.findall(text)
    scripts = _script_scores(text)
    scores: Dict[str, float] = {}
    for code, spec in LANGUAGES.items():
        script_weight = scripts.get(spec.script, 0.0)
        marker_weight = _marker_hits(words, spec.markers)
        # Script decides the family; markers break ties inside a family.
        scores[code] = 0.55 * script_weight + 0.45 * marker_weight
        if script_weight == 0 and marker_weight == 0:
            scores[code] = 0.0

    if not any(scores.values()):
        return LanguageDetection("en", 0.35, signals={"default": 0.35, **scripts})

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_code, best_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    # Confidence rises with absolute score and how far ahead the winner is.
    margin = best_score - second
    confidence = min(1.0, max(0.2, 0.5 * best_score + 0.5 * (margin / max(best_score, 0.01))))
    if scripts.get(LANGUAGES[best_code].script, 0) < 0.2 and best_score < 0.15:
        return LanguageDetection("en", 0.4, signals={**scores, **scripts})
    return LanguageDetection(best_code, confidence, signals={**scores, **scripts})


def detect_language(text: str, requested: str = AUTO) -> str:
    """Backward-compatible helper used by the tutor and channels."""
    return detect_language_with_confidence(text, requested).code
