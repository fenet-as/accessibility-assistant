"""Offline hybrid retrieval over course chunks, for English and Amharic (Ethiopic) text.

Ranking = BM25 (unchanged core, k1=1.5, b=0.75) combined with:
- query-term coverage (IDF-weighted share of the question the section actually contains),
- title matching (section + lesson title), keyword matching (curated keywords + synonyms),
- exact phrase matching (consecutive query words appearing in the same order),
- synonym matching at reduced weight.
Course and lesson filters select the candidate set *before* anything is scored,
so content from another course can never be ranked or returned.

The index is immutable once built: a reload builds a new index and swaps the reference.
"""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from assistant.domain.models import Passage
from assistant.infrastructure.chunk_store import Chunk
from assistant.infrastructure.text_analysis import analyze, phrase_bigrams, synonyms_of

SYNONYM_WEIGHT = 0.6
WEIGHT_BM25, WEIGHT_COVERAGE, WEIGHT_TITLE, WEIGHT_KEYWORD, WEIGHT_PHRASE = 0.40, 0.30, 0.15, 0.05, 0.10
CONFIDENCE_COVERAGE, CONFIDENCE_TITLE, CONFIDENCE_PHRASE = 0.70, 0.15, 0.15


def _matches_scope(chunk: Chunk, scope: Optional[str]) -> bool:
    if not scope or scope in ("all", "auto"):
        return True
    return chunk.get("scope") == scope or chunk.get("course") == scope


@dataclass
class RetrievalResult:
    query_terms: List[str]
    passages: List[Passage]
    term_weights: Dict[str, float] = field(default_factory=dict)
    bonuses: Dict[str, float] = field(default_factory=dict)

    @property
    def top_confidence(self) -> float:
        return self.passages[0].confidence if self.passages else 0.0

    def combined_confidence(self, passages: List[Passage]) -> float:
        """Confidence that a *set* of passages together covers the question."""
        total = sum(self.term_weights.values())
        if not passages or total <= 0:
            return 0.0
        covered = {t for p in passages for t in p.matched_terms}
        coverage = sum(self.term_weights[t] for t in covered if t in self.term_weights) / total
        bonus = max(self.bonuses.get(p.id, 0.0) for p in passages)
        return round(min(1.0, CONFIDENCE_COVERAGE * coverage + bonus), 3)


class BM25Index:
    def __init__(self, chunks: Iterable[Chunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = list(chunks)
        self._postings: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        self._doc_lengths: List[int] = []
        self._doc_terms: List[FrozenSet[str]] = []
        self._title_terms: List[FrozenSet[str]] = []
        self._keyword_terms: List[FrozenSet[str]] = []
        self._doc_bigrams: List[Set[Tuple[str, str]]] = []
        self._idf: Dict[str, float] = {}
        self._build()

    def __len__(self) -> int:
        return len(self.chunks)

    def _build(self) -> None:
        for doc_id, chunk in enumerate(self.chunks):
            title_text = f"{chunk['section']} {chunk['title']}"
            body_text = " ".join([chunk["text"], *chunk.get("translations", {}).values()])
            title = analyze(title_text)
            keywords = analyze(" ".join([chunk.get("keywords_en", ""), chunk.get("keywords_am", ""),
                                         " ".join(chunk.get("synonyms", []))]))
            body = analyze(body_text)
            # Section and keywords appear twice so they weigh more than body text (as before).
            tokens = title * 2 + keywords * 2 + body

            self._title_terms.append(frozenset(title))
            self._keyword_terms.append(frozenset(keywords))
            self._doc_terms.append(frozenset(tokens))
            self._doc_bigrams.append(phrase_bigrams(title_text) | phrase_bigrams(body_text))
            self._doc_lengths.append(len(tokens))
            for term, freq in Counter(tokens).items():
                self._postings[term].append((doc_id, freq))

        n_docs = len(self.chunks)
        self._avg_doc_len = (sum(self._doc_lengths) / n_docs) if n_docs else 1.0
        self._idf = {
            term: math.log((n_docs - len(posts) + 0.5) / (len(posts) + 0.5) + 1.0)
            for term, posts in self._postings.items()
        }
        # A term the corpus has never seen weighs as much as its rarest known term: missing it lowers confidence.
        self._unseen_idf = max(self._idf.values(), default=1.0)

    def _bm25(self, term: str, doc_id: int, tf: int) -> float:
        length_norm = 1 - self.b + self.b * (self._doc_lengths[doc_id] / self._avg_doc_len)
        return self._idf[term] * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)

    def candidates(self, scope: Optional[str] = None, lesson: Optional[str] = None) -> List[int]:
        return [
            doc_id for doc_id, chunk in enumerate(self.chunks)
            if _matches_scope(chunk, scope) and (not lesson or chunk.get("lesson_id") == lesson)
        ]

    def section_titles(self, scope: Optional[str] = None, lesson: Optional[str] = None) -> List[str]:
        return [self.chunks[i]["section"] for i in self.candidates(scope, lesson)]

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        scope: Optional[str] = None,
        lesson: Optional[str] = None,
    ) -> RetrievalResult:
        query_terms = list(dict.fromkeys(analyze(query)))
        allowed = set(self.candidates(scope, lesson))
        if not query_terms or not allowed:
            return RetrievalResult(query_terms, [])

        weights = {t: self._idf.get(t, self._unseen_idf) for t in query_terms}
        total_weight = sum(weights.values()) or 1.0
        query_bigrams = phrase_bigrams(query)

        bm25: Dict[int, float] = defaultdict(float)
        matched: Dict[int, Dict[str, float]] = defaultdict(dict)
        for term in query_terms:
            exact_docs: Set[int] = set()
            if term in self._idf:
                for doc_id, tf in self._postings[term]:
                    if doc_id in allowed:
                        bm25[doc_id] += self._bm25(term, doc_id, tf)
                        matched[doc_id][term] = 1.0
                        exact_docs.add(doc_id)
            for synonym in synonyms_of(term):
                if synonym not in self._idf:
                    continue
                for doc_id, tf in self._postings[synonym]:
                    if doc_id in allowed and doc_id not in exact_docs:
                        bm25[doc_id] += SYNONYM_WEIGHT * self._bm25(synonym, doc_id, tf)
                        matched[doc_id].setdefault(term, SYNONYM_WEIGHT)

        if not bm25:
            return RetrievalResult(query_terms, [], weights)

        max_bm25 = max(bm25.values())
        scored, bonuses = [], {}
        for doc_id, raw in bm25.items():
            coverage = sum(weights[t] * w for t, w in matched[doc_id].items()) / total_weight
            title = sum(weights[t] for t in query_terms if t in self._title_terms[doc_id]) / total_weight
            keyword = sum(weights[t] for t in query_terms if t in self._keyword_terms[doc_id]) / total_weight
            phrase = (len(query_bigrams & self._doc_bigrams[doc_id]) / len(query_bigrams)) if query_bigrams else 0.0

            rank = (WEIGHT_BM25 * raw / max_bm25 + WEIGHT_COVERAGE * coverage + WEIGHT_TITLE * title
                    + WEIGHT_KEYWORD * keyword + WEIGHT_PHRASE * phrase)
            bonus = CONFIDENCE_TITLE * title + CONFIDENCE_PHRASE * phrase
            confidence = min(1.0, CONFIDENCE_COVERAGE * coverage + bonus)
            bonuses[self.chunks[doc_id]["id"]] = bonus
            scored.append((rank, raw, confidence, doc_id))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        passages = [
            self._to_passage(doc_id, rank, confidence, sorted(matched[doc_id]))
            for rank, _, confidence, doc_id in scored[:top_k]
        ]
        return RetrievalResult(query_terms, passages, weights, bonuses)

    def search(
        self,
        query: str,
        top_k: int = 3,
        scope: Optional[str] = None,
        lesson: Optional[str] = None,
    ) -> List[Passage]:
        return self.retrieve(query, top_k, scope, lesson).passages

    def serialize(self) -> Dict[str, object]:
        """Export the inverted index so the offline widget can score with the same BM25 parameters."""
        tfs_by_doc: List[Dict[str, int]] = [{} for _ in self.chunks]
        for term, posts in self._postings.items():
            for doc_id, tf in posts:
                tfs_by_doc[doc_id][term] = tf
        docs = [{
            "chunk": chunk,
            "length": self._doc_lengths[doc_id],
            "tfs": tfs_by_doc[doc_id],
            "title_terms": sorted(self._title_terms[doc_id]),
            "keyword_terms": sorted(self._keyword_terms[doc_id]),
            "bigrams": [list(pair) for pair in sorted(self._doc_bigrams[doc_id])],
        } for doc_id, chunk in enumerate(self.chunks)]
        return {
            "k1": self.k1,
            "b": self.b,
            "avg_doc_len": self._avg_doc_len,
            "unseen_idf": self._unseen_idf,
            "idf": dict(self._idf),
            "docs": docs,
        }

    def _to_passage(self, doc_id: int, score: float, confidence: float, matched_terms: List[str]) -> Passage:
        chunk = self.chunks[doc_id]
        return Passage(
            id=chunk["id"],
            scope=chunk.get("scope", ""),
            course=chunk["course"],
            lesson_id=chunk.get("lesson_id", ""),
            title=chunk["title"],
            section=chunk["section"],
            anchor=chunk.get("anchor", ""),
            url=chunk.get("url", ""),
            text=chunk["text"],
            translations=chunk.get("translations", {}),
            score=round(score, 3),
            confidence=round(confidence, 3),
            matched_terms=matched_terms,
        )
