"""Flexible multilingual course-name matching against the live chunk catalog.

Canonical course IDs always come from chunks (``scope``). Verified aliases live in
``course_alias_data.DEFAULT_COURSE_ALIASES`` and are validated against that catalog.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

from assistant.infrastructure.chunk_store import ChunkStore
from assistant.services.course_alias_data import DEFAULT_COURSE_ALIASES

logger = logging.getLogger(__name__)

# UI / channel sentinels that mean "no course pinned yet".
_OPEN_SCOPES = frozenset({"", "all", "auto", "none", "course:auto", "course:all"})

_PUNCT_RE = re.compile(r"[\s\-_/.,:;|+()\[\]{}'\"`~!?]+")
_LATIN_WORD_RE = re.compile(r"[a-z0-9]+", re.I)
# Ethiopic | Arabic | Latin tokens for span extraction.
_TOKEN_RE = re.compile(
    r"[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF]+|[\u0600-\u06FF]+|[A-Za-z0-9]+"
)


def normalize_course_text(text: str) -> str:
    """Casefold + strip punctuation/hyphens into single spaces (script-safe)."""
    raw = unicodedata.normalize("NFKC", text or "").casefold().strip()
    raw = _PUNCT_RE.sub(" ", raw)
    return " ".join(raw.split())


def compact_course_text(text: str) -> str:
    """Normalized text with all whitespace removed (virtualassistant == virtual assistant)."""
    return normalize_course_text(text).replace(" ", "")


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _adaptive_fuzzy_threshold(name_len: int) -> float:
    """Longer names tolerate relatively more absolute typos; short names stay strict."""
    if name_len <= 4:
        return 0.92
    if name_len <= 8:
        return 0.86
    if name_len <= 16:
        return 0.80
    return 0.74


def _ambiguity_margin(top_score: float) -> float:
    return 0.08 if top_score >= 0.9 else 0.10


@dataclass(frozen=True)
class CourseRecord:
    scope: str
    canonical_name: str
    search_names: Tuple[str, ...] = ()
    abbreviations: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()  # flattened multilingual + spelling variants
    primary_search_phrase: str = ""  # inserted into retrieval queries when rewriting

    @property
    def display_name(self) -> str:
        return self.canonical_name or self.scope


@dataclass(frozen=True)
class CourseCandidate:
    scope: str
    display_name: str
    score: float
    method: str  # exact | normalized | compact | alias | fuzzy | partial | abbreviation | ui_scope
    matched_alias: str = ""
    matched_span: str = ""  # exact substring from the learner message when known


@dataclass
class CourseResolution:
    scope: str
    display_name: str
    confidence: float
    method: str
    rewritten_message: str
    matched_alias: str = ""
    ambiguous: bool = False
    candidates: List[CourseCandidate] = field(default_factory=list)
    original_message: str = ""
    normalized_message: str = ""
    ui_scope_honored: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.scope) and not self.ambiguous


def _split_course_title(course_field: str) -> List[str]:
    """'VA-1: VA Foundations & Professional Identity' → useful searchable pieces."""
    text = (course_field or "").strip()
    if not text:
        return []
    parts = [text]
    if ":" in text:
        left, right = text.split(":", 1)
        parts.extend([left.strip(), right.strip()])
    for piece in list(parts):
        for bit in re.split(r"[&/|]", piece):
            bit = bit.strip()
            if bit and bit not in parts:
                parts.append(bit)
    return [p for p in parts if p]


class CourseMatcher:
    """Build a catalog from ChunkStore + validated aliases; resolve names in learner messages."""

    def __init__(
        self,
        store: ChunkStore,
        *,
        alias_config: Optional[Dict[str, Any]] = None,
    ):
        self.store = store
        self.alias_config = alias_config if alias_config is not None else DEFAULT_COURSE_ALIASES
        self._records: Dict[str, CourseRecord] = {}
        self._alias_index: List[Tuple[str, str, str]] = []  # (norm, compact, scope)
        self.reload()

    def reload(self) -> None:
        catalog = self._catalog_from_store()
        alias_cfg = self.alias_config or {}
        self._records = self._merge(catalog, alias_cfg)
        self._alias_index = []
        for record in self._records.values():
            names = (
                [record.canonical_name, record.primary_search_phrase]
                + list(record.search_names)
                + list(record.aliases)
                + list(record.abbreviations)
            )
            for name in names:
                norm = normalize_course_text(name)
                compact = compact_course_text(name)
                if norm:
                    self._alias_index.append((norm, compact, record.scope))
        logger.info(
            "course_matcher ready courses=%s alias_entries=%s",
            len(self._records),
            len(self._alias_index),
        )

    def known_scopes(self) -> List[str]:
        return sorted(self._records.keys())

    def get(self, scope: str) -> Optional[CourseRecord]:
        return self._records.get(scope)

    def is_known_scope(self, scope: Optional[str]) -> bool:
        return bool(scope) and scope not in _OPEN_SCOPES and scope in self._records

    def resolve(
        self,
        message: str,
        ui_scope: Optional[str] = None,
        *,
        language: str = "auto",
    ) -> CourseResolution:
        original = message or ""
        normalized = normalize_course_text(original)
        ui = (ui_scope or "").strip()
        ui_known = self.is_known_scope(ui)

        scored = self._score_message(original, language=language)
        scored.sort(key=lambda c: c.score, reverse=True)

        logger.info(
            "course_match original=%r normalized=%r ui_scope=%s language=%s candidates=%s",
            original[:200],
            normalized[:200],
            ui,
            language,
            [(c.scope, round(c.score, 3), c.method, c.matched_alias[:40]) for c in scored[:5]],
        )

        # Explicit UI course selection always wins for retrieval scope.
        if ui_known:
            record = self._records[ui]
            rewritten = self._rewrite_message(original, scored, preferred_scope=ui)
            return CourseResolution(
                scope=ui,
                display_name=record.display_name,
                confidence=1.0,
                method="ui_scope",
                rewritten_message=rewritten,
                matched_alias="",
                ambiguous=False,
                candidates=scored[:5],
                original_message=original,
                normalized_message=normalized,
                ui_scope_honored=True,
            )

        if not scored:
            return CourseResolution(
                scope="",
                display_name="",
                confidence=0.0,
                method="none",
                rewritten_message=original,
                original_message=original,
                normalized_message=normalized,
            )

        top = scored[0]
        ambiguous = False
        if len(scored) > 1:
            second = scored[1]
            if (
                second.scope != top.scope
                and second.score >= max(0.72, top.score - _ambiguity_margin(top.score))
                and top.score >= 0.72
            ):
                ambiguous = True

        accept = top.score >= self._accept_threshold(top)
        if ambiguous or not accept:
            logger.info(
                "course_match unresolved ambiguous=%s top=%s score=%.3f",
                ambiguous,
                top.scope,
                top.score,
            )
            return CourseResolution(
                scope="",
                display_name="",
                confidence=top.score,
                method=top.method,
                rewritten_message=original,
                matched_alias=top.matched_alias,
                ambiguous=ambiguous or (accept is False and top.score >= 0.65 and len(scored) > 1),
                candidates=scored[:5],
                original_message=original,
                normalized_message=normalized,
            )

        record = self._records[top.scope]
        rewritten = self._rewrite_message(original, scored, preferred_scope=top.scope)
        logger.info(
            "course_match selected scope=%s method=%s score=%.3f alias=%r rewritten=%r",
            top.scope,
            top.method,
            top.score,
            top.matched_alias[:60],
            rewritten[:200],
        )
        return CourseResolution(
            scope=top.scope,
            display_name=record.display_name,
            confidence=top.score,
            method=top.method,
            rewritten_message=rewritten,
            matched_alias=top.matched_alias,
            ambiguous=False,
            candidates=scored[:5],
            original_message=original,
            normalized_message=normalized,
        )

    def _accept_threshold(self, candidate: CourseCandidate) -> float:
        if candidate.method in ("exact", "normalized", "compact", "alias", "abbreviation"):
            return 0.84
        if candidate.method == "partial":
            return 0.86
        # fuzzy
        return _adaptive_fuzzy_threshold(len(compact_course_text(candidate.matched_alias or candidate.display_name)))

    def _score_message(self, message: str, *, language: str) -> List[CourseCandidate]:
        text_norm = normalize_course_text(message)
        text_compact = compact_course_text(message)
        if not text_norm:
            return []

        best: Dict[str, CourseCandidate] = {}

        def consider(scope: str, score: float, method: str, alias: str, span: str = "") -> None:
            if score <= 0:
                return
            prev = best.get(scope)
            # Prefer higher score; on ties prefer the longer matched span (full course name > "assistant").
            span_len = len(span or alias or "")
            prev_span_len = len((prev.matched_span or prev.matched_alias) if prev else "")
            if prev is not None and (
                score < prev.score - 1e-9
                or (abs(score - prev.score) <= 1e-9 and span_len <= prev_span_len)
            ):
                return
            record = self._records[scope]
            best[scope] = CourseCandidate(
                scope=scope,
                display_name=record.display_name,
                score=min(score, 1.0),
                method=method,
                matched_alias=alias,
                matched_span=span or alias,
            )

        for record in self._records.values():
            names: List[Tuple[str, str]] = []
            for label in (
                [record.canonical_name, record.primary_search_phrase]
                + list(record.search_names)
                + list(record.aliases)
            ):
                if label:
                    names.append((label, "alias" if label in record.aliases else "exact"))
            for abbr in record.abbreviations:
                names.append((abbr, "abbreviation"))

            for label, kind in names:
                label_norm = normalize_course_text(label)
                label_compact = compact_course_text(label)
                if not label_norm:
                    continue

                # Exact / normalized equality on full message or as a contained phrase.
                if text_norm == label_norm:
                    consider(
                        record.scope,
                        1.0,
                        "normalized" if kind != "abbreviation" else "abbreviation",
                        label,
                        span=message.strip() or label,
                    )
                    continue
                if text_compact == label_compact and len(label_compact) >= 6:
                    consider(record.scope, 0.98, "compact", label, span=message.strip() or label)
                    continue

                # Abbreviation: whole-word only, and only if unambiguous across catalog.
                if kind == "abbreviation":
                    if self._abbr_hits(text_norm, label_norm) and self._abbr_is_unique(label_norm):
                        # Lower score than full-name matches so "assistant course" does not beat "virtul assistant".
                        consider(record.scope, 0.88, "abbreviation", label, span=label)
                    continue

                # Contained phrase (partial / alias in sentence) — require enough distinctive length.
                min_partial = 8 if kind == "alias" else 10
                if len(label_norm) >= min_partial and (
                    f" {label_norm} " in f" {text_norm} "
                    or text_norm.startswith(label_norm + " ")
                    or text_norm.endswith(" " + label_norm)
                ):
                    method = "alias" if kind == "alias" else "partial"
                    span = self._recover_span(message, label_norm) or label
                    consider(record.scope, 0.95 if kind == "alias" else 0.90, method, label, span=span)
                    continue

                # Compact containment: "virtualassistantcourse" contains "virtualassistant".
                if len(label_compact) >= 8 and label_compact in text_compact:
                    span = self._recover_compact_span(message, label_compact) or label
                    consider(record.scope, 0.94, "compact", label, span=span)
                    continue

                # Fuzzy against sliding windows of similar token length.
                for window in self._windows(text_norm, label_norm):
                    ratio = _fuzzy_ratio(window, label_norm)
                    threshold = _adaptive_fuzzy_threshold(len(label_compact) or len(label_norm))
                    if ratio >= threshold:
                        score = ratio * (0.98 if kind == "alias" else 0.96)
                        span = self._recover_span(message, window) or window
                        consider(record.scope, score, "fuzzy", label, span=span)
                    # Also compare compact forms for missing-space typos.
                    ratio_c = _fuzzy_ratio(compact_course_text(window), label_compact)
                    if label_compact and ratio_c >= threshold:
                        span = self._recover_span(message, window) or window
                        consider(record.scope, ratio_c * 0.97, "fuzzy", label, span=span)

        return list(best.values())

    def _abbr_hits(self, text_norm: str, abbr_norm: str) -> bool:
        if not abbr_norm:
            return False
        if " " in abbr_norm:
            return f" {abbr_norm} " in f" {text_norm} "
        # Word boundary for Latin abbreviations; Ethiopic/Arabic as token equality.
        if _LATIN_WORD_RE.fullmatch(abbr_norm):
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(abbr_norm)}(?![a-z0-9])", text_norm))
        return abbr_norm in text_norm.split()

    def _abbr_is_unique(self, abbr_norm: str) -> bool:
        hits = 0
        for record in self._records.values():
            for abbr in record.abbreviations:
                if normalize_course_text(abbr) == abbr_norm:
                    hits += 1
                    if hits > 1:
                        return False
        return hits == 1

    def _windows(self, text_norm: str, label_norm: str) -> List[str]:
        """Candidate spans of roughly the same token count as the label."""
        tokens = _TOKEN_RE.findall(text_norm)
        label_tokens = _TOKEN_RE.findall(label_norm)
        if not tokens or not label_tokens:
            return [text_norm]
        n = len(label_tokens)
        windows = [" ".join(tokens[i : i + n]) for i in range(0, max(1, len(tokens) - n + 1))]
        # Also try n-1 / n+1 for missing/extra words.
        if n > 1:
            windows.extend(" ".join(tokens[i : i + n - 1]) for i in range(0, max(1, len(tokens) - n + 2)))
        windows.extend(" ".join(tokens[i : i + n + 1]) for i in range(0, max(1, len(tokens) - n)))
        windows.append(text_norm)
        # Deduplicate while preserving order.
        seen = set()
        out = []
        for w in windows:
            if w and w not in seen:
                seen.add(w)
                out.append(w)
        return out

    def _rewrite_message(
        self,
        message: str,
        scored: Sequence[CourseCandidate],
        *,
        preferred_scope: str,
    ) -> str:
        """Replace the matched misspelled/compact course span with a BM25-friendly phrase."""
        record = self._records.get(preferred_scope)
        if not record:
            return message
        phrase = record.primary_search_phrase or next(iter(record.search_names), "") or "virtual assistant"
        match_span = ""
        match_alias = ""
        for c in scored:
            if c.scope == preferred_scope:
                match_span = c.matched_span or c.matched_alias
                match_alias = c.matched_alias
                break
        if match_span:
            rewritten = self._replace_ignore_case(message, match_span, phrase)
            if rewritten != message:
                return rewritten
        if match_alias:
            rewritten = self._replace_ignore_case(message, match_alias, phrase)
            if rewritten != message:
                return rewritten
        return self._expand_compact_aliases(message, record, phrase)

    @staticmethod
    def _recover_span(message: str, normalized_span: str) -> str:
        """Map a normalized window back to a case-preserving substring of the original message."""
        if not message or not normalized_span:
            return ""
        compact_target = compact_course_text(normalized_span)
        if not compact_target:
            return ""
        # Scan original with a loose character-class pattern.
        pattern = CourseMatcher._loose_pattern_from_compact(compact_target)
        if pattern is None:
            # Non-Latin: try direct casefold find on whitespace-normalized forms.
            msg_cf = message.casefold()
            needle = normalized_span.casefold()
            idx = msg_cf.find(needle)
            if idx >= 0:
                return message[idx : idx + len(needle)]
            return normalized_span
        found = pattern.search(message)
        return found.group(0) if found else ""

    @staticmethod
    def _recover_compact_span(message: str, compact: str) -> str:
        pattern = CourseMatcher._loose_pattern_from_compact(compact)
        if pattern is None:
            return ""
        found = pattern.search(message)
        return found.group(0) if found else ""

    def _expand_compact_aliases(self, message: str, record: CourseRecord, phrase: str) -> str:
        text = message
        # Sort longer first so "virtualassistantcourse" hits before "virtualassistant".
        variants = sorted(
            {compact_course_text(a) for a in list(record.aliases) + list(record.search_names) + list(record.abbreviations) if len(compact_course_text(a)) >= 6},
            key=len,
            reverse=True,
        )
        compact_msg = compact_course_text(message)
        for variant in variants:
            if variant and variant in compact_msg:
                # Replace the original run that compactifies to this variant.
                pattern = self._loose_pattern_from_compact(variant)
                if pattern:
                    new_text, n = pattern.subn(phrase, text, count=1)
                    if n:
                        return new_text
        return text

    @staticmethod
    def _loose_pattern_from_compact(compact: str) -> Optional[re.Pattern]:
        """Build a regex that matches the compact Latin string with optional separators."""
        if not compact or not compact.isascii():
            return None
        parts = []
        # Split into words by guessing common boundaries is hard; allow optional separators between every char group.
        # Better: allow optional [\s\-_]* between letters of the compact form.
        body = r"[\s\-_]*".join(re.escape(ch) for ch in compact)
        return re.compile(body, re.IGNORECASE)

    @staticmethod
    def _replace_ignore_case(message: str, old: str, new: str) -> str:
        if not old:
            return message
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        return pattern.sub(new, message, count=1)

    def _catalog_from_store(self) -> Dict[str, CourseRecord]:
        courses: Dict[str, CourseRecord] = {}
        for chunk in self.store.load():
            scope = (chunk.get("scope") or "").strip()
            if not scope:
                continue
            course_field = (chunk.get("course") or "").strip()
            existing = courses.get(scope)
            titles = _split_course_title(course_field)
            if existing is None:
                primary = titles[1] if len(titles) > 1 else (titles[0] if titles else scope)
                # Prefer a human course name without the VA-1: prefix when available.
                search = tuple(dict.fromkeys(titles))
                courses[scope] = CourseRecord(
                    scope=scope,
                    canonical_name=course_field or scope,
                    search_names=search,
                    abbreviations=tuple(),
                    aliases=tuple(),
                    primary_search_phrase=self._guess_primary_phrase(scope, course_field, search),
                )
            else:
                merged = tuple(dict.fromkeys(list(existing.search_names) + titles))
                courses[scope] = CourseRecord(
                    scope=existing.scope,
                    canonical_name=existing.canonical_name or course_field,
                    search_names=merged,
                    abbreviations=existing.abbreviations,
                    aliases=existing.aliases,
                    primary_search_phrase=existing.primary_search_phrase,
                )
        return courses

    @staticmethod
    def _guess_primary_phrase(scope: str, course_field: str, search: Tuple[str, ...]) -> str:
        lowered = [s for s in search if s]
        for candidate in lowered:
            if "virtual assistant" in candidate.casefold():
                return "Virtual Assistant"
        if scope.endswith("va-1") or "va-1" in scope:
            return "Virtual Assistant"
        if lowered:
            # Drop leading code prefixes like "VA-1".
            for s in lowered:
                if not re.match(r"^[a-z]{1,4}-?\d+$", s, re.I):
                    return s
            return lowered[0]
        return course_field or scope

    def _merge(
        self,
        catalog: Dict[str, CourseRecord],
        alias_cfg: Dict[str, Any],
    ) -> Dict[str, CourseRecord]:
        merged: Dict[str, CourseRecord] = dict(catalog)
        for scope, cfg in alias_cfg.items():
            if scope not in catalog:
                logger.warning(
                    "course alias entry %s ignored — scope not present in chunk catalog",
                    scope,
                )
                continue
            base = catalog[scope]
            search = list(base.search_names)
            for name in cfg.get("search_names") or []:
                if name and name not in search:
                    search.append(name)
            abbreviations = list(base.abbreviations)
            for abbr in cfg.get("abbreviations") or []:
                if abbr and abbr not in abbreviations:
                    abbreviations.append(abbr)
            aliases: List[str] = list(base.aliases)
            alias_block = cfg.get("aliases") or {}
            if isinstance(alias_block, dict):
                for _lang, values in alias_block.items():
                    for value in values or []:
                        if value and value not in aliases:
                            aliases.append(value)
            elif isinstance(alias_block, list):
                for value in alias_block:
                    if value and value not in aliases:
                        aliases.append(value)
            for variant in cfg.get("spelling_variants") or []:
                if variant and variant not in aliases:
                    aliases.append(variant)
            primary = (cfg.get("search_names") or [None])[0] or base.primary_search_phrase
            if cfg.get("search_names"):
                # Prefer first configured search name as rewrite target when it looks like a course name.
                primary = cfg["search_names"][0]
            merged[scope] = CourseRecord(
                scope=scope,
                canonical_name=cfg.get("canonical_name") or base.canonical_name,
                search_names=tuple(search),
                abbreviations=tuple(abbreviations),
                aliases=tuple(aliases),
                primary_search_phrase=primary or base.primary_search_phrase,
            )
        return merged
