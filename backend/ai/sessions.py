"""
AI clarification session store — Postgres-backed with in-memory fallback (BE-020).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID

import psycopg

from data.db import connect


@dataclass
class ClarificationSession:
    """Pending NL translation awaiting user answers."""

    session_id: str
    text: str
    questions: list[dict[str, Any]]
    answers: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    user_id: UUID | None = None


class ClarificationSessionStore:
    """Thread-safe in-memory session map with idle TTL eviction + optional user bind."""

    def __init__(self, ttl_minutes: float = 30.0) -> None:
        self._ttl_sec = max(ttl_minutes, 1.0) * 60.0
        self._sessions: dict[str, ClarificationSession] = {}
        self._lock = Lock()

    def create(
        self,
        text: str,
        questions: list[dict[str, Any]],
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession:
        """Create and store a new clarification session."""
        self._evict_expired()
        session = ClarificationSession(
            session_id=str(uuid.uuid4()),
            text=text,
            questions=questions,
            user_id=user_id,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(
        self,
        session_id: str,
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession | None:
        """Return a live session or None if missing/expired/wrong owner."""
        self._evict_expired()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if user_id is not None and session.user_id is not None and session.user_id != user_id:
                return None
            return session

    def update_answers(
        self,
        session_id: str,
        answers: dict[str, str],
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession | None:
        """Merge answers into an existing session."""
        self._evict_expired()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if user_id is not None and session.user_id is not None and session.user_id != user_id:
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


class PostgresClarificationSessionStore:
    """Persist clarification sessions in ``app.ai_clarify_sessions`` (BE-020)."""

    def __init__(self, ttl_minutes: float = 30.0) -> None:
        self._ttl = timedelta(minutes=max(ttl_minutes, 1.0))

    def create(
        self,
        text: str,
        questions: list[dict[str, Any]],
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession:
        if user_id is None:
            raise ValueError("user_id is required for Postgres clarify sessions")
        session_id = uuid.uuid4()
        now = datetime.now(tz=UTC)
        expires = now + self._ttl
        with connect() as conn:
            self._delete_expired(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app.ai_clarify_sessions
                        (session_id, user_id, text, questions, answers, created_at, updated_at, expires_at)
                    VALUES (%s, %s, %s, %s::jsonb, '{}'::jsonb, %s, %s, %s)
                    """,
                    (
                        session_id,
                        user_id,
                        text,
                        json.dumps(questions),
                        now,
                        now,
                        expires,
                    ),
                )
            conn.commit()
        return ClarificationSession(
            session_id=str(session_id),
            text=text,
            questions=questions,
            user_id=user_id,
            created_at=now.timestamp(),
            updated_at=now.timestamp(),
        )

    def get(
        self,
        session_id: str,
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession | None:
        with connect() as conn:
            self._delete_expired(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, user_id, text, questions, answers, created_at, updated_at
                    FROM app.ai_clarify_sessions
                    WHERE session_id = %s
                      AND (%s::uuid IS NULL OR user_id = %s)
                      AND expires_at > NOW()
                    """,
                    (session_id, user_id, user_id),
                )
                row = cur.fetchone()
            if row is None:
                return None
            return self._to_session(row)

    def update_answers(
        self,
        session_id: str,
        answers: dict[str, str],
        *,
        user_id: UUID | None = None,
    ) -> ClarificationSession | None:
        session = self.get(session_id, user_id=user_id)
        if session is None:
            return None
        session.answers.update({k: str(v) for k, v in answers.items()})
        now = datetime.now(tz=UTC)
        expires = now + self._ttl
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.ai_clarify_sessions
                    SET answers = %s::jsonb,
                        updated_at = %s,
                        expires_at = %s
                    WHERE session_id = %s
                      AND (%s::uuid IS NULL OR user_id = %s)
                    """,
                    (
                        json.dumps(session.answers),
                        now,
                        expires,
                        session_id,
                        user_id,
                        user_id,
                    ),
                )
            conn.commit()
        session.updated_at = now.timestamp()
        return session

    def delete(self, session_id: str) -> None:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM app.ai_clarify_sessions WHERE session_id = %s",
                    (session_id,),
                )
            conn.commit()

    def clear(self) -> None:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app.ai_clarify_sessions")
            conn.commit()

    def _delete_expired(self, conn: psycopg.Connection) -> None:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM app.ai_clarify_sessions WHERE expires_at <= NOW()")
        conn.commit()

    @staticmethod
    def _to_session(row: tuple[Any, ...]) -> ClarificationSession:
        questions = row[3]
        answers = row[4]
        if isinstance(questions, str):
            questions = json.loads(questions)
        if isinstance(answers, str):
            answers = json.loads(answers)
        return ClarificationSession(
            session_id=str(row[0]),
            user_id=row[1],
            text=row[2],
            questions=list(questions or []),
            answers=dict(answers or {}),
            created_at=row[5].timestamp() if hasattr(row[5], "timestamp") else float(row[5]),
            updated_at=row[6].timestamp() if hasattr(row[6], "timestamp") else float(row[6]),
        )


_STORE: ClarificationSessionStore | PostgresClarificationSessionStore | None = None
_USE_MEMORY = False


def get_session_store(
    ttl_minutes: float | None = None,
) -> ClarificationSessionStore | PostgresClarificationSessionStore:
    """Return the process-wide session store (Postgres in API; memory for unit tests)."""
    global _STORE
    if _STORE is None:
        import os

        minutes = (
            ttl_minutes
            if ttl_minutes is not None
            else float(os.environ.get("AI_CLARIFY_TTL_MINUTES", "30"))
        )
        backend = os.environ.get("AI_CLARIFY_STORE", "db").strip().lower()
        if _USE_MEMORY or backend in ("memory", "mem"):
            _STORE = ClarificationSessionStore(ttl_minutes=minutes)
        else:
            _STORE = PostgresClarificationSessionStore(ttl_minutes=minutes)
    return _STORE


def reset_session_store() -> None:
    """Reset the singleton (tests) — forces in-memory for subsequent gets."""
    global _STORE, _USE_MEMORY
    if _STORE is not None:
        try:
            _STORE.clear()
        except Exception:
            pass
    _STORE = None
    _USE_MEMORY = True
