"""Knowledge-base chunk schema (v2): course → lesson → section, with translations and versioning.

`scope` is the course id (for example `course:va-1`); `title` is the lesson title.
Chunks written before v2 load fine: missing fields are derived on the way in.
"""

import hashlib
import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator

from assistant.domain.language import SUPPORTED_LANGUAGES as LANGUAGE_CODES

SCHEMA_VERSION = 2
SUPPORTED_LANGUAGES = set(LANGUAGE_CODES)
MIN_TEXT_LENGTH = 20

COURSE_ID_PATTERN = re.compile(r"^course:[\w.-]+$")
ANCHOR_PATTERN = re.compile(r"^(#[^\s#]+)?$")


def slugify(text: str) -> str:
    """Convert a title into a URL-safe slug (Ethiopic letters are kept)."""
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def content_hash(section: str, text: str, translations: Dict[str, str]) -> str:
    payload = "\n".join([section.strip(), " ".join(text.split())] +
                        [f"{k}:{translations[k]}" for k in sorted(translations)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_kb_version(chunks: List[Dict[str, Any]]) -> str:
    """Stable identifier of the whole knowledge base; changes whenever any chunk changes."""
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda c: c["id"]):
        digest.update(f"{chunk['id']}={chunk['content_hash']};".encode("utf-8"))
    return digest.hexdigest()[:12]


class KnowledgeChunk(BaseModel):
    id: str
    scope: str = Field(..., description="Course id, e.g. course:va-1")
    course: str = Field(..., description="Course title")
    lesson_id: str = ""
    title: str = Field(..., description="Lesson title")
    section: str
    anchor: str = ""
    url: str
    language: str = "en"
    text: str
    translations: Dict[str, str] = Field(default_factory=dict)
    keywords_en: str = ""
    keywords_am: str = ""
    synonyms: List[str] = Field(default_factory=list)
    content_hash: str = ""
    revision: int = 1

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if not data.get("scope") and data.get("course", "").startswith("course:"):
                data["scope"] = data["course"]
            if not data.get("lesson_id") and data.get("title"):
                data["lesson_id"] = slugify(data["title"])
        return data

    @field_validator("id", "course", "title", "section", "lesson_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("scope")
    @classmethod
    def _valid_scope(cls, value: str) -> str:
        if not COURSE_ID_PATTERN.match(value):
            raise ValueError("must look like 'course:<id>'")
        return value

    @field_validator("text")
    @classmethod
    def _enough_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < MIN_TEXT_LENGTH:
            raise ValueError(f"must contain at least {MIN_TEXT_LENGTH} characters")
        return value

    @field_validator("anchor")
    @classmethod
    def _valid_anchor(cls, value: str) -> str:
        if not ANCHOR_PATTERN.match(value):
            raise ValueError("must be empty or '#' followed by an id without spaces")
        return value

    @field_validator("url")
    @classmethod
    def _valid_url(cls, value: str) -> str:
        if not value.startswith(("/", "http://", "https://")):
            raise ValueError("must be a root-relative path or an http(s) URL")
        return value

    @field_validator("language")
    @classmethod
    def _valid_language(cls, value: str) -> str:
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"must be one of {sorted(SUPPORTED_LANGUAGES)}")
        return value

    @field_validator("translations")
    @classmethod
    def _valid_translations(cls, value: Dict[str, str]) -> Dict[str, str]:
        unknown = set(value) - SUPPORTED_LANGUAGES
        if unknown:
            raise ValueError(f"unsupported languages: {sorted(unknown)}")
        return {lang: text.strip() for lang, text in value.items() if text and text.strip()}

    @model_validator(mode="after")
    def _fill_hash(self) -> "KnowledgeChunk":
        if not self.content_hash:
            self.content_hash = content_hash(self.section, self.text, self.translations)
        return self


def validate_chunks(raw_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate every chunk; raise one ValueError listing all problems so nothing invalid is indexed."""
    valid, errors = [], []
    for position, raw in enumerate(raw_chunks, start=1):
        try:
            valid.append(KnowledgeChunk.model_validate(raw).model_dump())
        except ValueError as exc:
            label = raw.get("section") or raw.get("id") or f"#{position}"
            problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'chunk'}: {e['msg']}" for e in exc.errors()) \
                if hasattr(exc, "errors") else str(exc)
            errors.append(f"section '{label}': {problems}")
    if errors:
        raise ValueError("Invalid content: " + " | ".join(errors))
    return valid
