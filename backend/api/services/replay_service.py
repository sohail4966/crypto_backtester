"""
Replay session facade delegating to ``ReplaySessionStore`` and ``ReplayEngine``.

Thin entry point for REST routes and WebSocket handler. All replay state
mutations flow through the store (DB + in-memory cache).
"""

from __future__ import annotations

from uuid import UUID

import psycopg

from api.exceptions import NotFoundError
from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplaySessionCreate, ReplayStateResponse
from api.services.replay_engine import ReplayEngine
from api.services.replay_session_store import ReplaySessionStore


class ReplayService:
    """Create and control open-ended bar replay sessions (Phase 4c)."""

    def __init__(self, store: ReplaySessionStore | None = None) -> None:
        """
        Args:
            store: Session store (default: process-wide store instance).
        """
        self._store = store or ReplaySessionStore()

    def create_session(
        self,
        conn: psycopg.Connection,
        body: ReplaySessionCreate,
        *,
        user_id: UUID,
    ) -> ReplayEngine:
        """
        Create a DB-backed replay session with initial buffer.

        Args:
            conn: Database connection.
            body: Open-ended session configuration.
            user_id: Owning user from JWT (BE-006).

        Returns:
            Engine with buffer loaded; connect WS at returned ``ws_url``.
        """
        return self._store.create(conn, body, user_id=user_id)

    def require_session(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> None:
        """
        Ensure a replay session row exists (and optionally is owned by ``user_id``).

        Raises:
            NotFoundError: When the session does not exist or ownership mismatches
                (404 to avoid existence leak — BE-006).
        """
        row = self._store.get_row(conn, session_id)
        if user_id is not None and row.user_id != user_id:
            raise NotFoundError("REPLAY_NOT_FOUND", f"Unknown replay session: {session_id}")

    def get_engine(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> ReplayEngine:
        """
        Return the replay engine for a session.

        Rebuilds buffer from DB when cache was evicted.
        """
        if user_id is not None:
            self.require_session(conn, session_id, user_id=user_id)
        return self._store.get_engine(conn, session_id)

    def delete_session(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> None:
        """Tear down a session (database row + memory cache)."""
        if user_id is not None:
            self.require_session(conn, session_id, user_id=user_id)
        self._store.delete(conn, session_id)

    def to_state_response(self, engine: ReplayEngine) -> ReplayStateResponse:
        """
        Build a REST/WS state snapshot from an engine.

        Args:
            engine: Live replay engine.

        Returns:
            Serializable session state.
        """
        return engine.to_state_response()

    def checkpoint(self, conn: psycopg.Connection, session_id: UUID, *, force: bool = False) -> None:
        """
        Persist cursor checkpoint to the database.

        Args:
            conn: Database connection.
            session_id: Session UUID.
            force: Skip interval throttle (pause, disconnect, seek).
        """
        self._store.checkpoint(conn, session_id, force=force)

    def update_indicators(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        indicators: list[IndicatorSpec],
    ) -> ReplayEngine:
        """
        Replace indicator specs and reload buffer.

        Args:
            conn: Database connection.
            session_id: Session UUID.
            indicators: New indicator specifications.

        Returns:
            Engine with recomputed overlays.
        """
        return self._store.update_indicators(conn, session_id, indicators)

    def consume_autoplay(self, session_id: UUID) -> bool:
        """
        Return whether the session should auto-send the first tick batch on WS connect.

        Args:
            session_id: Session UUID.

        Returns:
            ``True`` once when ``autoplay`` was set at session create.
        """
        return self._store.consume_autoplay(session_id)


_replay_service: ReplayService | None = None


def get_replay_service() -> ReplayService:
    """Return the process-wide singleton ``ReplayService``."""
    global _replay_service
    if _replay_service is None:
        _replay_service = ReplayService()
    return _replay_service
