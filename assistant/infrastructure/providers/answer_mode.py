"""Answer modes for generative providers. Retrieval decides the mode; the mode decides the prompt."""

from __future__ import annotations

COURSE = "course"  # Passages are evidence; general knowledge must be labeled separately.
GENERAL = "general"  # No course evidence; answer from general knowledge; never invent citations.

SENTINEL_NOT_FOUND = "NOT_FOUND"
SENTINEL_OUT_OF_SCOPE = "OUT_OF_SCOPE"
GENERAL_HEADING = "General explanation"
