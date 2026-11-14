"""Frozen copy of the retrieval engine before Milestone 1, used only to produce the comparison report.

Do not import this from application code.
"""

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "find", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "make", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "use", "used", "uses", "using", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself", "yourselves",
    "ነው", "ናቸው", "ነበር", "እና", "ውስጥ", "ላይ", "ወይ", "ወይም", "ስለ", "ወደ", "እስከ", "እንደ", "ጋር",
    "አለ", "አይደለም", "ምን", "እንዴት", "ማን", "የት",
}
DOMAIN_SYNONYMS = [("va", ("virtual", "assistant")), ("ai", ("artificial", "intelligence"))]
TOKEN_PATTERN = re.compile(r"[\u1200-\u137F]+|[a-zA-Z0-9]+")
SECTION_MATCH_BOOST = 0.5
REJECTION_THRESHOLD = 0.35


def tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    if not text:
        return []
    tokens = TOKEN_PATTERN.findall(text.lower())
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOP_WORDS]
    return tokens


def expand_synonyms(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    present = set(tokens)
    for acronym, words in DOMAIN_SYNONYMS:
        if acronym in present:
            expanded.extend(w for w in words if w not in present)
        elif all(w in present for w in words):
            expanded.append(acronym)
    return expanded


def _indexed_text(chunk: Dict[str, Any]) -> str:
    section = chunk.get("section", "")
    kw_en = chunk.get("keywords_en", "")
    kw_am = chunk.get("keywords_am", "")
    return f"{section} {section} {kw_en} {kw_en} {kw_am} {kw_am} {chunk.get('text', '')}"


def _matches_scope(chunk: Dict[str, Any], scope: Optional[str]) -> bool:
    if not scope or scope in ("all", "auto"):
        return True
    return chunk.get("scope") == scope or chunk.get("course") == scope


class BaselineBM25:
    def __init__(self, chunks: Iterable[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks = list(chunks)
        self._postings: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        self._section_tokens: List[Set[str]] = []
        self._doc_lengths: List[int] = []
        for doc_id, chunk in enumerate(self.chunks):
            self._section_tokens.append(set(tokenize(f"{chunk.get('section', '')} {chunk.get('title', '')}", True)))
            tokens = expand_synonyms(tokenize(_indexed_text(chunk)))
            self._doc_lengths.append(len(tokens))
            for term, freq in Counter(tokens).items():
                self._postings[term].append((doc_id, freq))
        n = len(self.chunks)
        self._avg = (sum(self._doc_lengths) / n) if n else 1.0
        self._idf = {t: math.log((n - len(p) + 0.5) / (len(p) + 0.5) + 1.0) for t, p in self._postings.items()}

    def search(self, query: str, top_k: int = 3, scope: Optional[str] = None) -> List[Tuple[Dict[str, Any], float]]:
        q = tokenize(query, remove_stopwords=True)
        if not q or not self.chunks:
            return []
        scores: Dict[int, float] = defaultdict(float)
        for term in expand_synonyms(q):
            idf = self._idf.get(term)
            if idf is None:
                continue
            for doc_id, tf in self._postings[term]:
                if not _matches_scope(self.chunks[doc_id], scope):
                    continue
                norm = 1 - self.b + self.b * (self._doc_lengths[doc_id] / self._avg)
                scores[doc_id] += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
        qset = set(q)
        for doc_id in scores:
            hits = len(qset & self._section_tokens[doc_id])
            if hits:
                scores[doc_id] *= 1.0 + SECTION_MATCH_BOOST * hits
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [(self.chunks[i], s) for i, s in ranked]

    def decide(self, query: str, scope: Optional[str]) -> Tuple[str, List[Dict[str, Any]]]:
        """Old TutorService rule: answer if the top BM25 score clears 0.35, else not_found."""
        results = self.search(query, 3, scope)
        if not results or results[0][1] < REJECTION_THRESHOLD:
            return "not_found", [c for c, _ in results]
        return "answer", [c for c, _ in results]
