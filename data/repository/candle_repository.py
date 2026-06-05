"""
Candle repository — executes native SQL from queries.py against TimescaleDB.

Mirrors a Spring Data JpaRepository with @Query(nativeQuery = true): one class per
aggregate (candles), methods map to named SQL, no inline SQL in callers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import psycopg

from data.db import connect
from data.repository import queries

CandleRow = tuple[Any, ...]
WriteRow = tuple[str, str, Any, float, float, float, float, float]

REQUIRED_COLUMNS = {"ts", "open", "high", "low", "close", "volume"}
DERIVED_INTERVALS = {
    "5m": "5 minutes",
    "15m": "15 minutes",
    "1h": "1 hour",
    "4h": "4 hours",
    "1d": "1 day",
}


def _to_write_rows(symbol: str, timeframe: str, candles: pd.DataFrame) -> list[WriteRow]:
    """
    Convert a candle DataFrame into positional rows for the candle write statements.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution string.
        candles: DataFrame with columns ts, open, high, low, close, volume.

    Returns:
        Rows ordered as (symbol, timeframe, ts, open, high, low, close, volume).

    Raises:
        ValueError: If required columns are missing.
    """
    if not REQUIRED_COLUMNS.issubset(candles.columns):
        raise ValueError(f"candles DataFrame must contain columns: {REQUIRED_COLUMNS}")
    return [
        (
            symbol,
            timeframe,
            row.ts.to_pydatetime() if hasattr(row.ts, "to_pydatetime") else row.ts,
            float(row.open),
            float(row.high),
            float(row.low),
            float(row.close),
            float(row.volume),
        )
        for row in candles.itertuples(index=False)
    ]


def _to_derived_interval(timeframe: str) -> str:
    """
    Convert an API timeframe string into a SQL interval literal for aggregation.

    Args:
        timeframe: Requested timeframe, e.g. 1d.

    Returns:
        SQL interval text understood by time_bucket.

    Raises:
        ValueError: If the timeframe is not supported for derived reads.
    """
    if timeframe not in DERIVED_INTERVALS:
        raise ValueError(
            f"Unsupported derived timeframe: {timeframe}. Supported: {sorted(DERIVED_INTERVALS)}"
        )
    return DERIVED_INTERVALS[timeframe]


class CandleRepository:
    """
    Persistence layer for OHLCV candles.

    All reads and writes go through this class so SQL stays centralized in queries.py.
    Schema changes are applied via data.migrations on startup, not here.
    """

    def upsert_many(
        self,
        symbol: str,
        timeframe: str,
        candles: pd.DataFrame,
        conn: psycopg.Connection | None = None,
    ) -> int:
        """
        Insert or update OHLCV rows for a symbol and timeframe.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            candles: DataFrame with columns ts, open, high, low, close, volume.
            conn: Optional existing connection.

        Returns:
            Number of rows written.

        Raises:
            ValueError: If required columns are missing.

        Side effects:
            Commits rows to the database.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        # Upsert via ON CONFLICT — safe to re-run fetch without duplicate key errors.
        rows = _to_write_rows(symbol, timeframe, candles)
        try:
            with conn.cursor() as cur:
                cur.executemany(queries.UPSERT_CANDLE, rows)
            conn.commit()
            return len(rows)
        finally:
            if own_conn:
                conn.close()

    def insert_new_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: pd.DataFrame,
        conn: psycopg.Connection | None = None,
    ) -> int:
        """
        Insert closed candles without overwriting candles already stored.

        Used by incremental sync: existing closed bars stay immutable
        (overwrite_closed_candles=false), and duplicate rows are ignored.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            candles: DataFrame with columns ts, open, high, low, close, volume.
            conn: Optional existing connection.

        Returns:
            Number of rows actually inserted (conflicts are not counted).

        Raises:
            ValueError: If required columns are missing.

        Side effects:
            Commits rows to the database.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        rows = _to_write_rows(symbol, timeframe, candles)
        try:
            with conn.cursor() as cur:
                cur.executemany(queries.INSERT_CANDLE_IGNORE, rows)
                # rowcount excludes rows skipped by ON CONFLICT DO NOTHING.
                inserted = cur.rowcount
            conn.commit()
            return max(int(inserted), 0)
        finally:
            if own_conn:
                conn.close()

    def count(
        self,
        symbol: str,
        timeframe: str,
        conn: psycopg.Connection | None = None,
    ) -> int:
        """
        Count stored candles for a symbol and timeframe.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            conn: Optional existing connection.

        Returns:
            Number of matching rows.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.COUNT_CANDLES, (symbol, timeframe))
                (row_count,) = cur.fetchone()
                return int(row_count)
        finally:
            if own_conn:
                conn.close()

    def latest_timestamp(
        self,
        symbol: str,
        timeframe: str,
        conn: psycopg.Connection | None = None,
    ) -> datetime | None:
        """
        Return the most recent stored candle timestamp for a symbol and timeframe.

        Used by incremental sync to resume fetching from the latest closed candle.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            conn: Optional existing connection.

        Returns:
            The maximum ts as a timezone-aware datetime, or None when no rows exist.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.SELECT_MAX_TS, (symbol, timeframe))
                # MAX() over zero rows returns a single (None,) row, not an empty result.
                (max_ts,) = cur.fetchone()
                return max_ts
        finally:
            if own_conn:
                conn.close()

    def find_timestamps(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        conn: psycopg.Connection | None = None,
    ) -> list[datetime]:
        """
        Return stored candle timestamps in an inclusive range, ascending.

        Used by gap detection, which only needs timestamps rather than full OHLCV rows.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            start: Inclusive start date (ISO).
            end: Inclusive end date (ISO).
            conn: Optional existing connection.

        Returns:
            Timestamps as timezone-aware datetimes, empty when no rows match.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.SELECT_TS_BY_RANGE, (symbol, timeframe, start, end))
                return [row[0] for row in cur.fetchall()]
        finally:
            if own_conn:
                conn.close()

    def find_by_date_range(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        conn: psycopg.Connection | None = None,
    ) -> tuple[list[CandleRow], list[str]]:
        """
        Load OHLCV rows for a symbol, timeframe, and inclusive date range.

        Args:
            symbol: Trading pair identifier.
            timeframe: Candle resolution string.
            start: Inclusive start date (ISO).
            end: Inclusive end date (ISO).
            conn: Optional existing connection.

        Returns:
            Tuple of (rows, column_names) from the native SELECT.
        """
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    queries.SELECT_CANDLES_BY_RANGE,
                    (symbol, timeframe, start, end),
                )
                rows = cur.fetchall()
                column_names = [col.name for col in cur.description]
                return rows, column_names
        finally:
            if own_conn:
                conn.close()

    def find_derived_by_date_range(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        conn: psycopg.Connection | None = None,
    ) -> tuple[list[CandleRow], list[str]]:
        """
        Derive non-1m candles from stored canonical 1m rows in an inclusive date range.

        Args:
            symbol: Trading pair identifier.
            timeframe: Requested derived timeframe (5m, 15m, 1h, 4h, 1d).
            start: Inclusive start date (ISO).
            end: Inclusive end date (ISO).
            conn: Optional existing connection.

        Returns:
            Tuple of (rows, column_names) of derived OHLCV candles ordered by ts.

        Raises:
            ValueError: If timeframe is unsupported for derived reads.
        """
        interval = _to_derived_interval(timeframe)
        own_conn = conn is None
        if own_conn:
            conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    queries.SELECT_DERIVED_CANDLES_BY_RANGE,
                    (symbol, start, end, interval),
                )
                rows = cur.fetchall()
                column_names = [col.name for col in cur.description]
                return rows, column_names
        finally:
            if own_conn:
                conn.close()
