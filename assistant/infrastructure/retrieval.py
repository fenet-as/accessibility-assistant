"""Offline BM25 retrieval over course chunks, for English and Amharic (Ethiopic) text.

The index is immutable once built: a reload builds a new `BM25Index` and swaps the
reference, so concurrent requests never observe a partially rebuilt index.
Queries walk an inverted index, so cost grows with matching documents, not corpus size.
"""

import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from assistant.domain.models import Passage
from assistant.infrastructure.chunk_store import Chunk

STOP_WORDS: Set[str] = {
    # English
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
    # Amharic particles
    "ነው", "ናቸው", "ነበር", "እና", "ውስጥ", "ላይ", "ወይ", "ወይም", "ስለ", "ወደ", "እስከ", "እንደ", "ጋር",
    "አለ", "አይደለም", "ምን", "እንዴት", "ማን", "የት",
}

# Acronym <-> expansion pairs, so "VA" matches "virtual assistant" and vice versa.
DOMAIN_SYNONYMS: List[Tuple[str, Tuple[str, ...]]] = [
    ("va", ("virtual", "assistant")),
    ("ai", ("artificial", "intelligence")),
]

TOKEN_PATTERN = re.compile(r"[\u1200-\u137F]+|[a-zA-Z0-9]+")
SECTION_MATCH_BOOST = 0.5


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


def _indexed_text(chunk: Chunk) -> str:
    """Section and keywords appear twice so they weigh more than body text."""
    section = chunk.get("section", "")
    keywords_en = chunk.get("keywords_en", "")
    keywords_am = chunk.get("keywords_am", "")
    return f"{section} {section} {keywords_en} {keywords_en} {keywords_am} {keywords_am} {chunk.get('text', '')}"


def _matches_scope(chunk: Chunk, scope: Optional[str]) -> bool:
    if not scope or scope in ("all", "auto"):
        return True
    return chunk.get("scope") == scope or chunk.get("course") == scope


class BM25Index:
    def __init__(self, chunks: Iterable[Chunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = list(chunks)
        self._postings: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        self._section_tokens: List[Set[str]] = []
        self._doc_lengths: List[int] = []
        self._idf: Dict[str, float] = {}
        self._build()

    def __len__(self) -> int:
        return len(self.chunks)

    def _build(self) -> None:
        for doc_id, chunk in enumerate(self.chunks):
            section_text = f"{chunk.get('section', '')} {chunk.get('title', '')}"
            self._section_tokens.append(set(tokenize(section_text, remove_stopwords=True)))

            tokens = expand_synonyms(tokenize(_indexed_text(chunk)))
            self._doc_lengths.append(len(tokens))
            for term, freq in Counter(tokens).items():
                self._postings[term].append((doc_id, freq))

        n_docs = len(self.chunks)
        self._avg_doc_len = (sum(self._doc_lengths) / n_docs) if n_docs else 1.0
        self._idf = {
            term: math.log((n_docs - len(posts) + 0.5) / (len(posts) + 0.5) + 1.0)
            for term, posts in self._postings.items()
        }

    def search(self, query: str, top_k: int = 3, scope: Optional[str] = None) -> List[Passage]:
        query_tokens = tokenize(query, remove_stopwords=True)
        if not query_tokens or not self.chunks:
            return []

        scores: Dict[int, float] = defaultdict(float)
        for term in expand_synonyms(query_tokens):
            idf = self._idf.get(term)
            if idf is None:
                continue
            for doc_id, tf in self._postings[term]:
                if not _matches_scope(self.chunks[doc_id], scope):
                    continue
                length_norm = 1 - self.b + self.b * (self._doc_lengths[doc_id] / self._avg_doc_len)
                scores[doc_id] += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)

        query_set = set(query_tokens)
        for doc_id in scores:
            section_hits = len(query_set & self._section_tokens[doc_id])
            if section_hits:
                scores[doc_id] *= 1.0 + SECTION_MATCH_BOOST * section_hits

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [self._to_passage(doc_id, score) for doc_id, score in ranked]

    def _to_passage(self, doc_id: int, score: float) -> Passage:
        chunk = self.chunks[doc_id]
        return Passage(
            id=chunk["id"],
            course=chunk["course"],
            title=chunk["title"],
            section=chunk["section"],
            anchor=chunk.get("anchor", ""),
            url=chunk.get("url", ""),
            text=chunk["text"],
            score=round(score, 3),
        )
