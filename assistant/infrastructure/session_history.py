"""Short per-session conversation memory for channels that cannot send history (Telegram, SMS).

The web widget already sends recent turns in ChatRequest.history. This buffer fills the gap
for other channels so follow-ups like "What are its advantages?" resolve correctly.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import List

from assistant.domain.models import ConversationTurn

DEFAULT_MAX_TURNS = 6
DEFAULT_MAX_SESSIONS = 500
DEFAULT_TTL_SECONDS = 3600


class SessionHistoryStore:
    def __init__(
        self,
        *,
        max_turns: int = DEFAULT_MAX_TURNS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self.max_turns = max_turns
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._sessions: "OrderedDict[str, tuple[float, List[ConversationTurn]]]" = OrderedDict()

    def get(self, session: str) -> List[ConversationTurn]:
        key = (session or "").strip()
        if not key:
            return []
        now = time.time()
        with self._lock:
            item = self._sessions.get(key)
            if not item:
                return []
            expires, turns = item
            if expires < now:
                del self._sessions[key]
                return []
            self._sessions.move_to_end(key)
            return list(turns)

    def append(self, session: str, user_message: str, assistant_message: str) -> None:
        key = (session or "").strip()
        if not key:
            return
        now = time.time()
        with self._lock:
            item = self._sessions.get(key)
            turns: List[ConversationTurn] = list(item[1]) if item and item[0] >= now else []
            if user_message:
                turns.append(ConversationTurn(role="user", content=user_message))
            if assistant_message:
                turns.append(ConversationTurn(role="assistant", content=assistant_message))
            if len(turns) > self.max_turns:
                turns = turns[-self.max_turns :]
            self._sessions[key] = (now + self.ttl_seconds, turns)
            self._sessions.move_to_end(key)
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)

    def clear(self, session: str = "") -> None:
        with self._lock:
            if session:
                self._sessions.pop(session.strip(), None)
            else:
                self._sessions.clear()
