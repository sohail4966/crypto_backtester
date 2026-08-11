"""
In-memory clarification session store (D-113).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class ClarificationSession:
    """Pending NL translation awaiting user answers."""

    session_id: str
    text: str
    questions: list[dict[str, Any]]
    answers: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ClarificationSessionStore:
    """Thread-safe in-memory session map with idle TTL eviction."""

    def __init__(self, ttl_minutes: float = 30.0) -> None:
        self._ttl_sec = max(ttl_minutes, 1.0) * 60.0
        self._sessions: dict[str, ClarificationSession] = {}
        self._lock = Lock()

    def create(self, text: str, questions: list[dict[str, Any]]) -> ClarificationSession:
        """Create and store a new clarification session."""
        self._evict_expired()
        session = ClarificationSession(
            session_id=str(uuid.uuid4()),
            text=text,
            questions=questions,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ClarificationSession | None:
        """Return a live session or None if missing/expired."""
        self._evict_expired()
        with self._lock:
            return self._sessions.get(session_id)

    def update_answers(
        self,
        session_id: str,
        answers: dict[str, str],
    ) -> ClarificationSession | None:
        """Merge answers into an existing session."""
        self._evict_expired()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.answers.update({k: str(v) for k, v in answers.items()})
            session.updated_at = time.time()
            return session

    def delete(self, session_id: str) -> None:
        """Drop a session after successful translation."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear(self) -> None:
        """Remove all sessions (tests)."""
        with self._lock:
            self._sessions.clear()

    def _evict_expired(self) -> None:
        """Drop sessions idle longer than TTL."""
        now = time.time()
        with self._lock:
            expired = [
                sid
                for sid, sess in self._sessions.items()
                if now - sess.updated_at > self._ttl_sec
            ]
            for sid in expired:
                del self._sessions[sid]


_STORE: ClarificationSessionStore | None = None


def get_session_store(ttl_minutes: float | None = None) -> ClarificationSessionStore:
    """Return the process-wide session store (lazy singleton)."""
    global _STORE
    if _STORE is None:
        import os

        minutes = (
            ttl_minutes
            if ttl_minutes is not None
            else float(os.environ.get("AI_CLARIFY_TTL_MINUTES", "30"))
        )
        _STORE = ClarificationSessionStore(ttl_minutes=minutes)
    return _STORE


def reset_session_store() -> None:
    """Reset the singleton (tests)."""
    global _STORE
    if _STORE is not None:
        _STORE.clear()
    _STORE = None
