"""
Gap repository — CRUD for the data_gaps audit table (TimescaleDB).

Records missing 1m candle ranges so sync can retry and resolve them. Gap *detection*
(deriving ranges from candle continuity) lands in Step 4; this class only persists,
lists, retries, and resolves gap rows. SQL is centralized in queries.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg

from data.db import connect
from data.repository import queries


@dataclass(frozen=True)
class Gap:
    """A recorded missing candle range for one symbol/timeframe."""

    id: int
    symbol: str
    timeframe: str
    start_ts: datetime
    end_ts: datetime
    status: str
    retry_count: int


class GapRepository:
    """
    Persistence layer for data_gaps rows.

    Open gaps represent ranges where expected candles are missing. Sync retries them
    on later passes and marks them resolved once the candles exist.
    """

    def create_gap(
        self,
        symbol: str,
        timeframe: str,
        start_ts: datetime,
        end_ts: datetime,
        conn: psycopg.Connection | None = None,
    ) -> int:
        """
        Insert a new open gap for a missing candle range.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            start_ts: First missing candle timestamp (inclusive).
            end_ts: Last missing candle timestamp (inclusive).
            conn: Optional existing connection.

        Returns:
            The id of the newly created gap row.

        Side effects:
            Commits a row to the database.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.INSERT_GAP, (symbol, timeframe, start_ts, end_ts))
                (gap_id,) = cur.fetchone()
            conn.commit()
            return int(gap_id)
        finally:
            if own_conn:
                conn.close()

    def find_open_gaps(
        self,
        symbol: str,
        timeframe: str,
        conn: psycopg.Connection | None = None,
    ) -> list[Gap]:
        """
        List still-open gaps for a symbol and timeframe, oldest first.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            conn: Optional existing connection.

        Returns:
            Open gaps ordered by start_ts ascending; empty when none are open.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.SELECT_OPEN_GAPS, (symbol, timeframe))
                rows = cur.fetchall()
                return [Gap(*row) for row in rows]
        finally:
            if own_conn:
                conn.close()

    def mark_gap_resolved(
        self,
        gap_id: int,
        conn: psycopg.Connection | None = None,
    ) -> None:
        """
        Mark a gap resolved once its missing candles have been backfilled.

        Args:
            gap_id: Identifier of the gap to resolve.
            conn: Optional existing connection.

        Side effects:
            Commits the status change to the database.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.RESOLVE_GAP, (gap_id,))
            conn.commit()
        finally:
            if own_conn:
                conn.close()

    def record_gap_retry(
        self,
        gap_id: int,
        last_error: str | None = None,
        conn: psycopg.Connection | None = None,
    ) -> None:
        """
        Increment a gap's retry count and record when it was last attempted.

        Args:
            gap_id: Identifier of the gap that was retried.
            last_error: Optional error message from the failed retry, if any.
            conn: Optional existing connection.

        Side effects:
            Commits the retry bookkeeping to the database.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.RECORD_GAP_RETRY, (last_error, gap_id))
            conn.commit()
        finally:
            if own_conn:
                conn.close()
