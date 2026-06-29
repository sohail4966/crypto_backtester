"""
Repository for ``app.replay_sessions`` persistence.

Stores replay session metadata and cursor checkpoints. The hot OHLCV buffer
lives in memory only (see ``ReplaySessionStore``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import psycopg

from api.repositories import queries
from api.schemas.indicators import IndicatorSpec

ReplayState = Literal["idle", "playing", "paused", "completed"]


@dataclass
class ReplaySessionRow:
    """
    One row from ``app.replay_sessions``.

    Attributes:
        session_id: Primary key.
        symbol: Trading pair (FK to ``app.symbols``).
        timeframe: Chart display timeframe (e.g. ``1h``).
        step_timeframe: Bar resolution used for replay stepping.
        start_anchor: User-selected replay start (unix seconds).
        cursor_ts: Last revealed bar time (checkpointed).
        indicators: Indicator specs stored as JSONB.
        speed: Last playback speed multiplier.
        state: Session playback state.
        created_at: Row creation time.
        updated_at: Last metadata or checkpoint update.
    """

    session_id: UUID
    symbol: str
    timeframe: str
    step_timeframe: str
    start_anchor: int
    cursor_ts: int
    indicators: list[IndicatorSpec]
    speed: float
    state: ReplayState
    created_at: datetime
    updated_at: datetime


def _row_to_session(row: tuple[Any, ...]) -> ReplaySessionRow:
    """Map a ``SELECT``/``RETURNING`` tuple to ``ReplaySessionRow``."""
    raw_indicators = row[6]
    if isinstance(raw_indicators, str):
        indicators_data = json.loads(raw_indicators)
    else:
        indicators_data = raw_indicators
    indicators = [IndicatorSpec.model_validate(item) for item in indicators_data]
    return ReplaySessionRow(
        session_id=row[0],
        symbol=row[1],
        timeframe=row[2],
        step_timeframe=row[3],
        start_anchor=int(row[4]),
        cursor_ts=int(row[5]),
        indicators=indicators,
        speed=float(row[7]),
        state=row[8],
        created_at=row[9],
        updated_at=row[10],
    )


def _indicators_json(specs: list[IndicatorSpec]) -> str:
    """Serialize indicator specs for JSONB column storage."""
    return json.dumps([spec.model_dump() for spec in specs])


class ReplayRepository:
    """CRUD and checkpoint updates for ``app.replay_sessions``."""

    def insert(
        self,
        conn: psycopg.Connection,
        *,
        session_id: UUID,
        symbol: str,
        timeframe: str,
        step_timeframe: str,
        start_anchor: int,
        cursor_ts: int,
        indicators: list[IndicatorSpec],
        speed: float,
        state: ReplayState,
    ) -> ReplaySessionRow:
        """
        Insert a new replay session row.

        Args:
            conn: Database connection.
            session_id: New session UUID.
            symbol: Active trading pair.
            timeframe: Chart display timeframe.
            step_timeframe: Bar step resolution.
            start_anchor: Replay start anchor (unix seconds).
            cursor_ts: Initial cursor (typically one bar before ``start_anchor``).
            indicators: Indicator specifications.
            speed: Initial playback speed.
            state: Initial playback state.

        Returns:
            The inserted row.

        Raises:
            RuntimeError: When ``INSERT`` returns no row.
        """
        with conn.cursor() as cur:
            cur.execute(
                queries.INSERT_REPLAY_SESSION,
                (
                    session_id,
                    symbol,
                    timeframe,
                    step_timeframe,
                    start_anchor,
                    cursor_ts,
                    _indicators_json(indicators),
                    speed,
                    state,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT replay session returned no row")
            return _row_to_session(row)

    def get(self, conn: psycopg.Connection, session_id: UUID) -> ReplaySessionRow | None:
        """
        Fetch one session by id.

        Args:
            conn: Database connection.
            session_id: Session UUID.

        Returns:
            Session row, or ``None`` when not found.
        """
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_REPLAY_SESSION, (session_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    def update_checkpoint(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        *,
        cursor_ts: int,
        speed: float,
        state: ReplayState,
    ) -> ReplaySessionRow | None:
        """
        Persist cursor position, speed, and playback state.

        Called periodically on pause, disconnect, or checkpoint interval.

        Args:
            conn: Database connection.
            session_id: Session UUID.
            cursor_ts: Last revealed bar time (unix seconds).
            speed: Current playback speed.
            state: Current playback state.

        Returns:
            Updated row, or ``None`` when session does not exist.
        """
        with conn.cursor() as cur:
            cur.execute(
                queries.UPDATE_REPLAY_SESSION_CURSOR,
                (cursor_ts, speed, state, session_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    def update_indicators(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        indicators: list[IndicatorSpec],
    ) -> ReplaySessionRow | None:
        """
        Replace the indicator specification list for a session.

        Args:
            conn: Database connection.
            session_id: Session UUID.
            indicators: New indicator specs.

        Returns:
            Updated row, or ``None`` when session does not exist.
        """
        with conn.cursor() as cur:
            cur.execute(
                queries.UPDATE_REPLAY_SESSION_INDICATORS,
                (_indicators_json(indicators), session_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    def delete(self, conn: psycopg.Connection, session_id: UUID) -> bool:
        """
        Delete a session row.

        Args:
            conn: Database connection.
            session_id: Session UUID.

        Returns:
            ``True`` when a row was removed, ``False`` when already absent.
        """
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_REPLAY_SESSION, (session_id,))
            return cur.rowcount > 0
