"""
BM25 Keyword & Multilingual Retrieval Engine.
Operates completely offline with zero external dependencies.
Filters common query stop-words, handles domain abbreviations (VA <-> Virtual Assistant, AI),
and applies section heading weighting to ensure high grounding precision.
"""

import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional
from assistant.core.models import Passage

# Common English and Amharic stop words that carry no semantic relevance
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
    "use", "used", "uses", "using", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "you", "your", "yours", "yourself", "yourselves",
    # Amharic common particles
    "ነው", "ናቸው", "ነበር", "እና", "ውስጥ", "ላይ", "ወይ", "ወይም", "ስለ", "ወደ", "እስከ", "እንደ", "ጋር",
    "አለ", "አይደለም", "ምን", "እንዴት", "ማን", "የት"
}


class BM25Retriever:
    def __init__(self, chunks_path: Path, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks_path = chunks_path
        self.passages: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.section_tokens: List[Set[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.df: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.load_corpus()

    def tokenize(self, text: str, remove_stopwords: bool = False) -> List[str]:
        """Tokenize text into words supporting both Latin and Ethiopic (Amharic) scripts."""
        if not text:
            return []
        tokens = re.findall(r"[\u1200-\u137F]+|[a-zA-Z0-9]+", text.lower())
        if remove_stopwords:
            tokens = [t for t in tokens if t not in STOP_WORDS]
        return tokens

    def expand_domain_synonyms(self, tokens: List[str]) -> List[str]:
        """Expand domain-specific acronyms and phrases (VA, AI)."""
        expanded = list(tokens)
        token_set = set(tokens)

        # VA <-> Virtual Assistant
        if "va" in token_set:
            if "virtual" not in token_set:
                expanded.append("virtual")
            if "assistant" not in token_set:
                expanded.append("assistant")
        elif "virtual" in token_set and "assistant" in token_set:
            if "va" not in token_set:
                expanded.append("va")

        # AI <-> Artificial Intelligence
        if "ai" in token_set:
            if "artificial" not in token_set:
                expanded.append("artificial")
            if "intelligence" not in token_set:
                expanded.append("intelligence")
        elif "artificial" in token_set and "intelligence" in token_set:
            if "ai" not in token_set:
                expanded.append("ai")

        return expanded

    def load_corpus(self):
        """Load chunks from disk and build BM25 statistics."""
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"Chunks file not found at: {self.chunks_path}")

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            self.passages = json.load(f)

        self.corpus_tokens = []
        self.section_tokens = []
        self.doc_lengths = []
        self.df = {}

        for p in self.passages:
            # Triple weight for section heading and keywords
            section_t = set(self.tokenize(f"{p.get('section', '')} {p.get('title', '')}", remove_stopwords=True))
            self.section_tokens.append(section_t)

            combined = (
                f"{p.get('section', '')} {p.get('section', '')} "
                f"{p.get('keywords_en', '')} {p.get('keywords_en', '')} "
                f"{p.get('keywords_am', '')} {p.get('keywords_am', '')} "
                f"{p.get('text', '')}"
            )
            tokens = self.tokenize(combined, remove_stopwords=False)
            tokens = self.expand_domain_synonyms(tokens)
            self.corpus_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))

            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] = self.df.get(t, 0) + 1

        n_docs = len(self.passages)
        self.avg_doc_len = sum(self.doc_lengths) / n_docs if n_docs > 0 else 1.0

        self.idf = {}
        for token, freq in self.df.items():
            self.idf[token] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    def reload(self):
        """Reload corpus from disk after an ingestion or deletion event."""
        self.load_corpus()

    def search(self, query: str, top_k: int = 3, scope: Optional[str] = None) -> List[Passage]:
        """Search corpus using BM25 scoring with optional course scope filter."""
        query_tokens = self.tokenize(query, remove_stopwords=True)
        if not query_tokens or not self.passages:
            return []

        expanded_query = self.expand_domain_synonyms(query_tokens)
        query_set = set(query_tokens)

        scores: List[Tuple[int, float]] = []

        for idx, (doc_tokens, doc_len) in enumerate(zip(self.corpus_tokens, self.doc_lengths)):
            p = self.passages[idx]
            # If scope is specified, skip passages that do not belong to this course
            if scope and scope not in ["all", "auto"]:
                chunk_scope = p.get("scope", "")
                chunk_course = p.get("course", "")
                matches = (
                    chunk_scope == scope or
                    chunk_course == scope or
                    scope.lower() in chunk_course.lower() or
                    (not chunk_scope and "va" in scope.lower() and "va" in chunk_course.lower())
                )
                if not matches:
                    continue

            doc_tf: Dict[str, int] = {}
            for t in doc_tokens:
                doc_tf[t] = doc_tf.get(t, 0) + 1

            score = 0.0
            matched_terms = 0

            for qt in expanded_query:
                if qt in doc_tf:
                    tf = doc_tf[qt]
                    idf_val = self.idf.get(qt, 0.0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf_val * (numerator / denominator)
                    matched_terms += 1

            # Give a boost if section title directly matches query terms
            section_matches = len(query_set.intersection(self.section_tokens[idx]))
            if section_matches > 0:
                score *= (1.0 + 0.5 * section_matches)

            if matched_terms > 0:
                scores.append((idx, score))

        if not scores:
            return []

        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Passage] = []
        for idx, s in scores[:top_k]:
            p = self.passages[idx]
            results.append(
                Passage(
                    id=p["id"],
                    course=p["course"],
                    title=p["title"],
                    section=p["section"],
                    anchor=p.get("anchor", ""),
                    url=p.get("url", ""),
                    text=p["text"],
                    score=round(s, 3)
                )
            )

        return results
