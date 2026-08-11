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
    """One row from ``app.replay_sessions``."""

    session_id: UUID
    user_id: UUID | None
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
    raw_indicators = row[7]
    if isinstance(raw_indicators, str):
        indicators_data = json.loads(raw_indicators)
    else:
        indicators_data = raw_indicators
    indicators = [IndicatorSpec.model_validate(item) for item in indicators_data]
    return ReplaySessionRow(
        session_id=row[0],
        user_id=row[1],
        symbol=row[2],
        timeframe=row[3],
        step_timeframe=row[4],
        start_anchor=int(row[5]),
        cursor_ts=int(row[6]),
        indicators=indicators,
        speed=float(row[8]),
        state=row[9],
        created_at=row[10],
        updated_at=row[11],
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
        user_id: UUID,
        symbol: str,
        timeframe: str,
        step_timeframe: str,
        start_anchor: int,
        cursor_ts: int,
        indicators: list[IndicatorSpec],
        speed: float,
        state: ReplayState,
    ) -> ReplaySessionRow:
        """Insert a new replay session row owned by ``user_id``."""
        with conn.cursor() as cur:
            cur.execute(
                queries.INSERT_REPLAY_SESSION,
                (
                    session_id,
                    user_id,
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
            conn.commit()
            return _row_to_session(row)

    def get(self, conn: psycopg.Connection, session_id: UUID) -> ReplaySessionRow | None:
        """Fetch one session by id."""
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
        """Persist cursor position, speed, and playback state."""
        with conn.cursor() as cur:
            cur.execute(
                queries.UPDATE_REPLAY_SESSION_CURSOR,
                (cursor_ts, speed, state, session_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            conn.commit()
            return _row_to_session(row)

    def update_indicators(
        self,
        conn: psycopg.Connection,
        session_id: UUID,
        indicators: list[IndicatorSpec],
    ) -> ReplaySessionRow | None:
        """Replace the indicator specification list for a session."""
        with conn.cursor() as cur:
            cur.execute(
                queries.UPDATE_REPLAY_SESSION_INDICATORS,
                (_indicators_json(indicators), session_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            conn.commit()
            return _row_to_session(row)

    def delete(self, conn: psycopg.Connection, session_id: UUID) -> bool:
        """Delete a session row."""
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_REPLAY_SESSION, (session_id,))
            conn.commit()
            return cur.rowcount > 0
