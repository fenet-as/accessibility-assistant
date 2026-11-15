"""Question classification for the hybrid tutor, without any AI call.

Classifying decides *what kind* of question this is; it never decides whether an answer
exists. Two steps keep it testable:

1. `read_signals` looks only at the text and the conversation history (pronouns that
   point back, explicit course references, language-switch requests, domain vocabulary).
2. `classify` combines those signals with the course retrieval score and the selected
   language. A low retrieval score means "no course evidence", not "unanswerable".
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from assistant.domain.messages import detect_social_response
from assistant.domain.models import ConversationTurn
from assistant.infrastructure.text_analysis import analyze, normalize_text
from assistant.services.careers import is_job_question


class QuestionType(str, Enum):
    GREETING = "greeting"
    COURSE = "course"
    GENERAL = "general"
    FOLLOW_UP = "follow_up"
    CAREER = "career"
    UNRELATED = "unrelated"
    AMBIGUOUS = "ambiguous"


class ScopePolicy(str, Enum):
    EDUCATION = "education"
    COURSE_ONLY = "course_only"
    OPEN = "open"

    @classmethod
    def parse(cls, value: Optional[str]) -> "ScopePolicy":
        try:
            return cls((value or "").strip().lower())
        except ValueError:
            return cls.EDUCATION


# Explicit "explain it in Amharic / በአማርኛ / af Oromootiin …" language-switch intents.
_LANGUAGE_SWITCH_PATTERNS = [
    (re.compile(r"\b(?:in|into)\s+amharic\b", re.I), "am"),
    (re.compile(r"\b(?:in|into)\s+english\b", re.I), "en"),
    (re.compile(r"\b(?:in|into)\s+tigrinya\b", re.I), "ti"),
    (re.compile(r"\b(?:in|into)\s+(?:afaan\s+)?oromo\b", re.I), "om"),
    (re.compile(r"\b(?:in|into)\s+somali\b", re.I), "so"),
    (re.compile(r"\b(?:in|into)\s+arabic\b", re.I), "ar"),
    (re.compile(r"በአማርኛ"), "am"),
    (re.compile(r"በእንግሊዝ(?:ኛ)?"), "en"),
    (re.compile(r"በትግርኛ"), "ti"),
    (re.compile(r"af\s+oromootiin", re.I), "om"),
    (re.compile(r"afaan\s+oromoo?tiin", re.I), "om"),
    (re.compile(r"\bsomaali\b", re.I), "so"),
    (re.compile(r"بالعربية"), "ar"),
]

_SWITCH_FILLER = re.compile(
    r"\b(?:explain|answer|answers|previous|last|translate|translation|again|please|repeat|say|write|"
    r"respond|reply|response|language|አብራራ\w*|ተርጉም\w*|ibsi)\b",
    re.I,
)

_TOKEN = re.compile(r"[\u0600-\u06FF]+|[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF]+|[a-z0-9']+")


def _norm_set(items: Sequence[str]) -> frozenset:
    return frozenset(normalize_text(i) for i in items)


# Words that only make sense with an earlier topic ("its advantages", "explain that").
_ANAPHORS = _norm_set([
    "it", "its", "itself", "this", "that", "these", "those", "they", "them", "their", "theirs",
    "ይህ", "ይህን", "ይሄ", "ያ", "ያንን", "እነዚህ", "እነዚያ", "ጥቅሙ", "ጥቅሞቹ", "ጉዳቱ", "ጉዳቶቹ",
    "እዚ", "እቲ", "እዚኦም", "kana", "sana", "isaa", "isaanii", "kan", "kaas", "taas", "kuwaas",
    "هذا", "هذه", "ذلك", "تلك", "مزاياه", "فوائده",
])
# "this course" / "that lesson" point at the course, not at the previous answer.
_DEICTIC_COURSE_NOUNS = _norm_set([
    "course", "lesson", "module", "unit", "chapter", "section", "page", "program", "programme", "class",
])
_ELLIPTICAL_START = re.compile(
    r"^(?:and|but|also|so|what about|how about|why not|why|more|another|example|for example|"
    r"give me (?:an|another|more|some) examples?|tell me more|explain (?:more|further)|go on|continue|"
    r"elaborate|simplify|in simpler? (?:terms|words)|summari[sz]e)\b"
)
_ETHIOPIC_FOLLOW_UP = _norm_set(["ተጨማሪ", "የበለጠ", "ምሳሌ", "ለምሳሌ", "ተወሳኺ", "ኣብነት"])
_OTHER_FOLLOW_UP = _norm_set(["fakkeenya", "tusaale", "مثال", "المزيد"])
_ELLIPTICAL_MAX_WORDS = 8
# Nouns that ask about some aspect of a topic without naming it ("What are the advantages?").
_RELATIONAL = frozenset(analyze(
    "advantage advantages disadvantage disadvantages benefit benefits drawback drawbacks pros cons "
    "example examples type types kind kinds category categories step steps risk risks challenge "
    "challenges requirement requirements difference differences reason reasons feature features "
    "purpose meaning definition detail details many else",
    remove_stopwords=True,
))
# Pointing-back words plus at most this many own topic words still read as a follow-up
# ("How does it help clients?", "What about remote work?").
_MAX_OWN_TERMS_FOR_ANAPHORA = 2

_COURSE_REFERENCE = re.compile(
    r"\b(?:courses?|lessons?|modules?|units?|chapters?|curriculum|syllabus|concept page|the reading|"
    r"class notes|taught|teach(?:es)?|according to)\b"
)
_COURSE_REFERENCE_OTHER = _norm_set([
    "ትምህርቱ", "ትምህርቴ", "ኮርሱ", "ምዕራፍ", "ትምህርቲ", "koorsii", "koorsada", "casharka",
    "الدورة", "الدرس", "المقرر",
])
# Meta words removed from course-reference questions before retrieval ("what did my lesson teach about X").
_COURSE_META_WORDS = frozenset([
    "course", "courses", "lesson", "lessons", "module", "modules", "unit", "chapter", "curriculum",
    "syllabus", "current", "teach", "teaches", "taught", "material", "materials", "according",
])

# Learning and career topics the assistant covers under the "education" scope policy.
_DOMAIN_WORDS = frozenset([
    "va", "vas", "ai", "cv", "crm", "alx", "savanna", "seo", "kpi", "sop",
])
_DOMAIN_PREFIXES = (
    "virtual", "assistant", "freelanc", "remote", "client", "customer", "career", "job", "employ",
    "hire", "hiring", "recruit", "portfolio", "resume", "interview", "salary", "invoice", "contract",
    "agency", "niche", "skill", "productiv", "schedul", "calendar", "email", "e-mail", "spreadsheet",
    "excel", "upwork", "fiverr", "linkedin", "digital", "online", "internet", "computer", "typing",
    "software", "tool", "chatgpt", "automat", "communicat", "business", "entrepreneur", "admin",
    "course", "lesson", "study", "learn", "professional", "workplace", "meeting", "zoom", "deadline",
    "time management", "organi", "project", "task", "marketing", "social media", "data entry",
    "bookkeep", "transcri", "teamwork", "leadership", "negotiat", "income", "earn", "side hustle",
    "work from home", "remote work", "office", "manager", "management", "certificat", "training",
)
_DOMAIN_SUBSTRINGS = _norm_set([
    "ቨርቹዋል", "ረዳት", "ሥራ", "ሙያ", "ፍሪላንስ", "ፍሪላንሲንግ", "ደንበኛ", "ክህሎት", "ችሎታ", "ትምህርት", "ኮርስ",
    "ኦንላይን", "ኢንተርኔት", "ኮምፒውተር", "ዲጂታል", "ቅጥር", "ደሞዝ", "ገቢ", "ክእለት", "ሞያ",
    "hojii", "dandeettii", "maamila", "barnoota", "koorsii", "interneetii", "dijitaalaa",
    "shaqo", "xirfad", "macmiil", "koorso", "cashar", "dijitaal", "waxbarasho",
    "عمل", "وظيف", "مهار", "عميل", "مساعد", "افتراضي", "دورة", "درس", "عن بعد", "رقمي", "تعلم",
])
_CAREER_WORDS = frozenset([
    "become", "career", "careers", "hired", "hire", "portfolio", "resume", "cv", "interview",
    "salary", "earn", "income", "upwork", "fiverr", "linkedin", "profile", "apply", "pricing", "rates",
])
_CAREER_SUBSTRINGS = _norm_set(["ሙያ", "ቅጥር", "ደሞዝ", "ገቢ", "xirfad", "مسار مهني", "وظيف"])


def parse_language_switch(message: str) -> Optional[str]:
    """Return a language code when the learner asks to switch response language."""
    text = (message or "").strip()
    if not text:
        return None
    for pattern, code in _LANGUAGE_SWITCH_PATTERNS:
        if pattern.search(text):
            return code
    return None


def strip_language_switch(message: str) -> str:
    """'What is a VA in Amharic?' → 'What is a VA?' (language names are not course topics)."""
    text = message or ""
    for pattern, _ in _LANGUAGE_SWITCH_PATTERNS:
        text = pattern.sub(" ", text)
    return " ".join(text.split())


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall(normalize_text(text))


def _has_anaphor(tokens: List[str]) -> bool:
    for i, token in enumerate(tokens):
        if token not in _ANAPHORS:
            continue
        following = tokens[i + 1] if i + 1 < len(tokens) else ""
        if token in ("this", "that", "these", "those") and following in _DEICTIC_COURSE_NOUNS:
            continue
        return True
    return False


def own_topic_terms(message: str) -> Tuple[str, ...]:
    """Stemmed content words of the message that name a topic (not 'advantages', 'types', …)."""
    return tuple(t for t in dict.fromkeys(analyze(message)) if t not in _RELATIONAL)


def refers_back(message: str) -> bool:
    """True when the message needs an earlier topic to be understood."""
    text = normalize_text(message or "").strip()
    tokens = _tokens(text)
    if not tokens:
        return False
    own = own_topic_terms(message)
    # A message that names its own topic ("Why does Python use indentation?") stands alone.
    if len(own) > _MAX_OWN_TERMS_FOR_ANAPHORA:
        return False
    if _has_anaphor(tokens):
        return True
    if len(tokens) <= _ELLIPTICAL_MAX_WORDS and (
        _ELLIPTICAL_START.match(text) or set(tokens) & (_ETHIOPIC_FOLLOW_UP | _OTHER_FOLLOW_UP)
    ):
        return True
    # Only relational words left ("How many types?", "What are the advantages?").
    return not own and bool(set(analyze(message)) & _RELATIONAL)


def references_course(message: str) -> bool:
    text = normalize_text(message or "")
    return bool(_COURSE_REFERENCE.search(text)) or any(m in text for m in _COURSE_REFERENCE_OTHER)


def strip_course_meta(message: str) -> str:
    """'What did my current VA lesson teach about X?' → the words that describe X."""
    kept = [w for w in re.split(r"(\W+)", message or "") if w.lower() not in _COURSE_META_WORDS]
    return " ".join("".join(kept).split())


def _matches_domain(text: str, words: frozenset, prefixes: Sequence[str], substrings: frozenset) -> bool:
    tokens = _tokens(text)
    if set(tokens) & words:
        return True
    if any(token.startswith(prefixes) for token in tokens if token.isascii()):
        return True
    padded = f" {' '.join(tokens)} "
    if any(f" {p}" in padded for p in prefixes if " " in p):
        return True
    return any(s in text for s in substrings)


def mentions_domain(message: str) -> bool:
    return _matches_domain(normalize_text(message or ""), _DOMAIN_WORDS, _DOMAIN_PREFIXES, _DOMAIN_SUBSTRINGS)


def mentions_career(message: str) -> bool:
    return _matches_domain(normalize_text(message or ""), _CAREER_WORDS, (), _CAREER_SUBSTRINGS)


def should_expand_follow_up(message: str) -> bool:
    """Whether retrieval should merge this message with the previous question."""
    return refers_back(message) or parse_language_switch(message) is not None


@dataclass(frozen=True)
class QuestionSignals:
    """What the text and the conversation alone say about a question."""

    social: bool
    job_listing: bool
    language_switch: Optional[str]
    prior_question: str
    refers_back: bool
    references_course: bool
    in_domain: bool
    career: bool

    @property
    def has_history(self) -> bool:
        return bool(self.prior_question)

    @property
    def is_follow_up(self) -> bool:
        return self.has_history and self.refers_back


@dataclass(frozen=True)
class Classification:
    type: QuestionType
    # False when the scope check could not be confirmed (no domain vocabulary for this language).
    scope_confirmed: bool = True


def last_user_question(history: Sequence[ConversationTurn], current: str = "") -> str:
    current_norm = (current or "").strip().lower()
    for turn in reversed(list(history or [])):
        if turn.role == "user" and turn.content.strip() and turn.content.strip().lower() != current_norm:
            return turn.content
    return ""


def _switch_without_topic(message: str) -> bool:
    """'Explain your previous answer in Amharic' names no topic; 'What is a VA in Amharic?' does."""
    return not own_topic_terms(_SWITCH_FILLER.sub(" ", strip_language_switch(message)))


def read_signals(message: str, history: Sequence[ConversationTurn]) -> QuestionSignals:
    switch = parse_language_switch(message)
    return QuestionSignals(
        social=detect_social_response(message, "en") is not None,
        job_listing=is_job_question(message),
        language_switch=switch,
        prior_question=last_user_question(history, message),
        refers_back=refers_back(message) or (switch is not None and _switch_without_topic(message)),
        references_course=references_course(message),
        in_domain=mentions_domain(message),
        career=mentions_career(message),
    )


def classify(
    signals: QuestionSignals,
    *,
    text_language: str,
    course_confidence: float,
    policy: ScopePolicy = ScopePolicy.EDUCATION,
    high_confidence: float = 0.6,
    low_confidence: float = 0.35,
) -> Classification:
    """Pick the question type. `course_confidence` is evidence strength, never a refusal reason.

    `text_language` is the language the message is written in (not the selected answer language):
    the domain vocabulary check is only trusted for English text.
    """
    if signals.social and not signals.language_switch:
        return Classification(QuestionType.GREETING)
    if signals.job_listing and not signals.language_switch:
        return Classification(QuestionType.CAREER)
    if signals.is_follow_up:
        return Classification(QuestionType.FOLLOW_UP)
    if signals.refers_back:
        return Classification(QuestionType.AMBIGUOUS)
    if signals.references_course or course_confidence >= high_confidence:
        return Classification(QuestionType.COURSE)

    in_domain = signals.in_domain or course_confidence >= low_confidence
    if in_domain or policy == ScopePolicy.OPEN:
        return Classification(QuestionType.CAREER if signals.career else QuestionType.GENERAL)
    # The domain vocabulary is reliable only for English; elsewhere the generator checks scope.
    if text_language == "en":
        return Classification(QuestionType.UNRELATED)
    return Classification(QuestionType.GENERAL, scope_confirmed=False)
