"""Tokenization, normalization and light stemming for English and Amharic (Ethiopic) text.

Amharic handling (no external models):
- Ethiopic punctuation (U+1360–U+1368, e.g. "።", "፣") is a separator, not part of a word.
- Homophone letter families are merged (ሐ/ኀ→ሀ, ሠ→ሰ, ዐ→አ, ፀ→ጸ), so "ሥራ" and "ስራ" match.
- Common prepositional prefixes (የ, ለ, በ, ከ, …) and plural/object suffixes (ዎች, ች, ን, …) are removed,
  and the last syllable is reduced to its 6th (consonant) form, so "ክህሎቶችን" and "ክህሎት" share a stem.
"""

import re
import unicodedata
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple

# Ethiopic letters and combining marks, plus the Supplement and Extended blocks; punctuation excluded.
ETHIOPIC_LETTERS = "\u1200-\u135F\u1380-\u139F\u2D80-\u2DDF"
TOKEN_PATTERN = re.compile(rf"[{ETHIOPIC_LETTERS}]+|[a-z0-9]+")
ETHIOPIC_SYLLABLE = re.compile(rf"[{ETHIOPIC_LETTERS}]")

STOP_WORDS: Set[str] = {
    # English
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "come", "comes", "could", "did", "do", "does", "doing", "down", "during", "each", "explain",
    "few", "find", "for", "from", "further", "get", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "know", "make", "me",
    "mean", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "please", "same", "she", "should", "so",
    "some", "such", "tell", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "use", "used", "uses", "using", "very", "was", "we", "were", "what", "when", "where", "which",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself", "yourselves",
    # English contraction fragments and single letter noise
    "s", "t", "d", "ll", "re", "ve", "m",
    # Amharic particles and question words
    "ነው", "ናቸው", "ነበር", "እና", "ውስጥ", "ላይ", "ወይ", "ወይም", "ስለ", "ወደ", "እስከ", "እንደ", "ጋር",
    "አለ", "አይደለም", "ምን", "ምንድን", "ምንድነው", "እንዴት", "ማን", "የት", "ያለው", "ይህ", "ያ", "ምንም",
    "ለምን", "ሆኑ", "ሆነ", "ናት", "ነች", "ይመስላል", "ዓይነት", "አይነት",
}

# Acronyms that stand for a multi-word phrase.
ACRONYMS: List[Tuple[str, Tuple[str, ...]]] = [
    ("va", ("virtual", "assistant")),
    ("ai", ("artificial", "intelligence")),
]

# Words treated as interchangeable for matching (at reduced weight). Stemmed at import time.
SYNONYM_GROUPS: List[Tuple[str, ...]] = [
    ("help", "support", "assist", "aid", "ይረዳል", "ያግዛል", "ይደግፋል", "ድጋፍ"),
    ("job", "career", "employment", "profession", "role"),
    ("client", "customer"),
    ("skill", "ability", "competence", "expertise"),
    ("future", "upcoming", "tomorrow"),
    ("tool", "software", "app", "application"),
    ("learn", "study", "train"),
    ("promising", "hopeful", "bright", "encouraging"),
    ("value", "appreciate", "prize", "want", "ይፈልጋሉ", "ዋጋ"),
    ("trend", "change", "shift", "force"),
    ("beginner", "aspiring", "new", "starting"),
    ("market", "industry"),
    ("ስራ", "ሙያ"),
    ("ደንበኛ", "ተገልጋይ"),
    ("ክህሎት", "ችሎታ"),
    (
        "category", "categories", "type", "types", "kind", "kinds",
        "distinction", "distinctions", "difference", "differences",
        "specialization", "specializations", "classification", "ክፍል", "ዓይነት",
    ),
]

# Homophone letter families: (row start to rewrite, canonical row start).
_HOMOPHONE_ROWS = [(0x1210, 0x1200), (0x1280, 0x1200), (0x1220, 0x1230), (0x12D0, 0x12A0), (0x1340, 0x1338)]
_AMHARIC_PREFIXES = ("እንደ", "ስለ", "ወደ", "የ", "ለ", "በ", "ከ")
_AMHARIC_SUFFIXES = ("ዎችን", "ዎች", "ችን", "ች", "ን", "ው")
_MIN_AMHARIC_STEM = 2
# Multi-letter prefixes are often part of the word itself ("ወደፊት" = future), so they need a longer remainder.
_MIN_STEM_AFTER_LONG_PREFIX = 3
_GLOTTAL_A = {"\u12a3": "\u12a0"}  # ኣ is written interchangeably with አ (and ዓ, which maps to ኣ)


def _normalize_ethiopic_char(ch: str) -> str:
    code = ord(ch)
    for row, canonical in _HOMOPHONE_ROWS:
        if row <= code < row + 7:
            ch = chr(canonical + code - row)
            break
    return _GLOTTAL_A.get(ch, ch)


def normalize_text(text: str) -> str:
    """Lowercase Latin, merge Ethiopic homophones, keep every Ethiopic letter."""
    text = unicodedata.normalize("NFC", text or "").lower()
    return "".join(_normalize_ethiopic_char(c) for c in text)


def _to_sixth_order(ch: str) -> str:
    code = ord(ch)
    if not (0x1200 <= code <= 0x135A):
        return ch
    offset = (code - 0x1200) % 8
    if offset > 6:
        return ch
    candidate = chr(code - offset + 5)
    return candidate if unicodedata.name(candidate, "") else ch


def stem_amharic(token: str) -> str:
    for prefix in _AMHARIC_PREFIXES:
        min_stem = _MIN_STEM_AFTER_LONG_PREFIX if len(prefix) > 1 else _MIN_AMHARIC_STEM
        if token.startswith(prefix) and len(token) - len(prefix) >= min_stem:
            token = token[len(prefix):]
            break
    for suffix in _AMHARIC_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_AMHARIC_STEM:
            token = token[: -len(suffix)]
            break
    return token[:-1] + _to_sixth_order(token[-1])


def stem_english(token: str) -> str:
    if len(token) <= 3 or token.isdigit():
        return token
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("sses"):
        token = token[:-2]
    elif token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    return token


def stem(token: str) -> str:
    return stem_amharic(token) if ETHIOPIC_SYLLABLE.match(token) else stem_english(token)


STOP_WORDS = {normalize_text(w) for w in STOP_WORDS}


def words(text: str) -> List[str]:
    """Normalized surface words, in order, without stemming (used for phrase matching)."""
    return TOKEN_PATTERN.findall(normalize_text(text))


def analyze(text: str, remove_stopwords: bool = True) -> List[str]:
    """Normalized, stop-word-free, stemmed tokens with acronyms expanded."""
    tokens = [t for t in words(text) if not (remove_stopwords and t in STOP_WORDS)]
    return [stem(t) for t in expand_acronyms(tokens)]


def phrase_bigrams(text: str) -> Set[Tuple[str, str]]:
    """Adjacent stemmed word pairs, keeping stop words in place ("while loop", "for loop")
    but ignoring pairs made only of stop words ("what is")."""
    tokens = words(text)
    return {
        (stem(a), stem(b)) for a, b in zip(tokens, tokens[1:])
        if not (a in STOP_WORDS and b in STOP_WORDS)
    }


def expand_acronyms(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    present = set(tokens)
    for acronym, phrase in ACRONYMS:
        if acronym in present:
            expanded.extend(w for w in phrase if w not in present)
        elif all(w in present for w in phrase):
            expanded.append(acronym)
    return expanded


def _build_synonym_index(groups: Iterable[Tuple[str, ...]]) -> Dict[str, FrozenSet[str]]:
    index: Dict[str, Set[str]] = {}
    for group in groups:
        stems = {stem(t) for word in group for t in words(word)}
        for s in stems:
            index.setdefault(s, set()).update(stems - {s})
    return {k: frozenset(v) for k, v in index.items()}


SYNONYMS: Dict[str, FrozenSet[str]] = _build_synonym_index(SYNONYM_GROUPS)


def synonyms_of(term: str) -> FrozenSet[str]:
    return SYNONYMS.get(term, frozenset())
