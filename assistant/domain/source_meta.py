"""Normalize how answers are labeled for clients (badges, analytics, offline packs).

`answer_source` stays for backward compatibility. `source_type` is the Phase 7 field
learners and the widget should prefer.
"""

from __future__ import annotations

from typing import Optional

from assistant.domain.models import ChatResponse

# Must match assistant.infrastructure.providers.answer_mode.GENERAL_HEADING.
_GENERAL_HEADING = "General explanation"

# Stable source_type values returned on ChatResponse.
COURSE_GROUNDED = "course_grounded"
GENERAL_KNOWLEDGE = "general_knowledge"
MIXED = "mixed"
LOCAL_COURSE = "local_course"
FAQ = "faq"
CACHE = "cache"
SOCIAL = "social"
CAREERS = "careers"
NONE = "none"

CONNECTIVITY_ONLINE = "online"
CONNECTIVITY_OFFLINE = "offline"


def resolve_source_type(response: ChatResponse) -> str:
    """Derive a learner-facing source_type from provider / answer_source / content."""
    status = getattr(response.status, "value", response.status)
    # Never label missing / out-of-scope replies as Gemini or course-grounded.
    if status in ("not_found", "out_of_scope", "needs_clarification", "needs_human"):
        if response.answer_source == "social":
            return SOCIAL
        if response.answer_source == "careers" or (response.provider or "") == "careers":
            return CAREERS
        return NONE
    if response.cache_hit or response.answer_source == "cache":
        return CACHE
    if response.answer_source == "social":
        return SOCIAL
    if (response.provider or "") == "careers" or response.answer_source == "careers":
        return CAREERS
    if response.answer_source == "cloud_general":
        return GENERAL_KNOWLEDGE
    if response.answer_source == "cloud":
        answer = response.answer or ""
        if _GENERAL_HEADING.lower() in answer.lower():
            return MIXED
        return COURSE_GROUNDED
    if response.answer_source == "faq":
        # FAQ fallback after a Gemini failure still counts as FAQ extractive.
        return FAQ
    if response.answer_source == "local":
        return LOCAL_COURSE
    if response.answer_source in (None, "none"):
        return NONE
    return response.answer_source or NONE


def apply_response_meta(
    response: ChatResponse,
    *,
    course_id: Optional[str] = None,
    connectivity: str = CONNECTIVITY_ONLINE,
) -> ChatResponse:
    """Fill course_id, connectivity, and source_type without dropping answer_source."""
    if course_id is not None:
        response.course_id = course_id
    response.connectivity = connectivity or CONNECTIVITY_ONLINE
    response.source_type = resolve_source_type(response)
    return response
