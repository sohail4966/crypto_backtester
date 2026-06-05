"""
Candle repository — executes native SQL from queries.py against TimescaleDB.

Mirrors a Spring Data JpaRepository with @Query(nativeQuery = true): one class per
aggregate (candles), methods map to named SQL, no inline SQL in callers.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import psycopg

from data.db import connect
from data.repository import queries

CandleRow = tuple[Any, ...]


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
        required = {"ts", "open", "high", "low", "close", "volume"}
        if not required.issubset(candles.columns):
            raise ValueError(f"candles DataFrame must contain columns: {required}")

        own_conn = conn is None
        if own_conn:
            conn = connect()
        # Upsert via ON CONFLICT — safe to re-run fetch without duplicate key errors.
        rows = [
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
        try:
            with conn.cursor() as cur:
                cur.executemany(queries.UPSERT_CANDLE, rows)
            conn.commit()
            return len(rows)
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
