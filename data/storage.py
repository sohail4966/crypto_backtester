"""
TimescaleDB write-side facade for candles.

Delegates to CandleRepository; schema is applied via run_migrations() on startup.
"""

from __future__ import annotations

import pandas as pd
import psycopg

from data.migrations import run_migrations
from data.repository import CandleRepository

_default_repository = CandleRepository()


def run_migrations_on_startup(conn: psycopg.Connection | None = None) -> int:
    """
    Apply pending Flyway-style SQL migrations from data/migrations/sql/.

    Call once at application startup before any reads or writes.

    Args:
        conn: Optional existing connection.

    Returns:
        Number of migrations applied in this run.
    """
    return run_migrations(conn=conn)


def init_schema(conn: psycopg.Connection | None = None) -> int:
    """
    Apply database migrations (alias for run_migrations_on_startup).

    Args:
        conn: Optional existing connection.

    Returns:
        Number of migrations applied in this run.
    """
    return run_migrations_on_startup(conn)


def insert_candles(
    symbol: str,
    timeframe: str,
    candles: pd.DataFrame,
    conn: psycopg.Connection | None = None,
) -> int:
    """
    Insert or upsert OHLCV rows into the candles table.

    Args:
        symbol: Trading pair identifier.
        timeframe: Candle resolution string.
        candles: DataFrame with columns ts, open, high, low, close, volume.
        conn: Optional existing connection.

    Returns:
        Number of rows written.

    Side effects:
        Commits rows to the database.
    """
    return _default_repository.upsert_many(symbol, timeframe, candles, conn)


def candle_count(
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
        Number of rows in the candles table for the pair.
    """
    return _default_repository.count(symbol, timeframe, conn)
