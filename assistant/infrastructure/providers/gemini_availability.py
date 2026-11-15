"""Gemini availability and quota cooldown — separate from plain internet connectivity.

Internet up does not mean Gemini is callable. A free-tier 429 means Gemini is temporarily
unavailable even though the backend and the learner's browser are online.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# When Google omits a retry hint, cool down long enough to stop burning the daily free tier.
DEFAULT_QUOTA_COOLDOWN_SECONDS = 3600.0
MAX_QUOTA_COOLDOWN_SECONDS = 24 * 3600.0

_RETRY_IN = re.compile(
    r"retry(?:\s+in)?\s+(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*(?:(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?)?",
    re.I,
)
_RETRY_DELAY_FIELD = re.compile(r"retrydelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s?", re.I)


def parse_retry_seconds(message: str) -> Optional[float]:
    """Extract a cooldown from Google's 'Please retry in …' text or RetryInfo retryDelay."""
    text = message or ""
    match = _RETRY_DELAY_FIELD.search(text.replace(" ", ""))
    if match:
        return min(float(match.group(1)), MAX_QUOTA_COOLDOWN_SECONDS)
    match = _RETRY_IN.search(text)
    if not match:
        return None
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        return None
    return min(total, MAX_QUOTA_COOLDOWN_SECONDS)


def classify_gemini_failure(exc: BaseException) -> Tuple[str, Optional[float]]:
    """Return (fallback_reason, optional_cooldown_seconds).

    Reasons: quota | auth | timeout | unavailable | error
    """
    text = str(exc).lower()
    name = str(getattr(type(exc), "__name__", "") or type(exc)).lower()
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    if isinstance(exc, TimeoutError) or "timeout" in text or "timeout" in name:
        return "timeout", None
    if code == 429 or any(token in text for token in ("429", "resource_exhausted", "quota")):
        return "quota", parse_retry_seconds(str(exc)) or DEFAULT_QUOTA_COOLDOWN_SECONDS
    if code in (401, 403) or any(token in text for token in ("api key", "permission_denied", "unauthenticated", "401", "403")):
        return "auth", None
    if code in (500, 502, 503, 504) or any(token in text or token in name for token in ("500", "502", "503", "504")):
        return "server", None
    if any(token in text or token in name for token in ("unavailable", "connection", "dns", "network")):
        return "unavailable", None
    return "error", None


def is_retryable_failure(reason: str) -> bool:
    """Quota and auth never recover within the same request; transient failures might."""
    return reason in ("timeout", "unavailable", "server")


@dataclass
class GeminiAvailability:
    """Thread-safe snapshot of whether Gemini can be called right now."""

    _lock: threading.Lock = threading.Lock()
    cooldown_until: float = 0.0
    last_reason: Optional[str] = None
    last_error: Optional[str] = None
    last_success_at: float = 0.0
    configured: bool = False
    sdk_loaded: bool = False
    model: str = ""

    def mark_success(self) -> None:
        with self._lock:
            self.cooldown_until = 0.0
            self.last_reason = None
            self.last_error = None
            self.last_success_at = time.time()

    def mark_failure(self, reason: str, detail: str = "", cooldown_seconds: Optional[float] = None) -> None:
        with self._lock:
            self.last_reason = reason
            self.last_error = (detail or "")[:300] or None
            if reason == "quota":
                wait = cooldown_seconds if cooldown_seconds is not None else DEFAULT_QUOTA_COOLDOWN_SECONDS
                self.cooldown_until = max(self.cooldown_until, time.time() + max(0.0, wait))

    def cooling_down(self) -> bool:
        with self._lock:
            return time.time() < self.cooldown_until

    def seconds_remaining(self) -> float:
        with self._lock:
            return max(0.0, self.cooldown_until - time.time())

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            remaining = max(0.0, self.cooldown_until - now)
            cooling = remaining > 0
            if not self.configured:
                status = "missing_key"
            elif not self.sdk_loaded:
                status = "missing_sdk"
            elif cooling:
                status = "quota_cooldown"
            elif self.last_reason == "auth":
                status = "auth_error"
            else:
                status = "ready"
            available = status == "ready"
            cooldown_until = None
            if cooling:
                cooldown_until = datetime.fromtimestamp(self.cooldown_until, tz=timezone.utc).isoformat()
            return {
                "configured": self.configured,
                "sdk_loaded": self.sdk_loaded,
                "model": self.model,
                "available": available,
                "status": status,
                "cooldown_remaining_seconds": round(remaining, 1) if cooling else 0.0,
                "cooldown_until": cooldown_until,
                "last_failure_reason": self.last_reason,
                "last_error": self.last_error,
                "last_success_at": (
                    datetime.fromtimestamp(self.last_success_at, tz=timezone.utc).isoformat()
                    if self.last_success_at
                    else None
                ),
            }
