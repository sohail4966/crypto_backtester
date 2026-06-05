"""
Tests for CandleRepository read metadata using a mocked database cursor.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd

from data.repository import queries
from data.repository.candle_repository import CandleRepository


def _conn_with_cursor(cursor: MagicMock) -> MagicMock:
    """Build a mock connection whose cursor() context manager yields the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn


def test_latest_timestamp_returns_none_when_table_empty() -> None:
    """MAX(ts) over no rows yields (None,), which maps to None."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (None,)
    conn = _conn_with_cursor(cursor)

    result = CandleRepository().latest_timestamp("BTC/USDT", "1m", conn=conn)

    assert result is None
    cursor.execute.assert_called_once_with(queries.SELECT_MAX_TS, ("BTC/USDT", "1m"))


def test_latest_timestamp_returns_max_when_populated() -> None:
    """The stored maximum timestamp is returned unchanged."""
    latest = datetime(2024, 1, 2, 3, 4, tzinfo=UTC)
    cursor = MagicMock()
    cursor.fetchone.return_value = (latest,)
    conn = _conn_with_cursor(cursor)

    result = CandleRepository().latest_timestamp("BTC/USDT", "1m", conn=conn)

    assert result == latest


def test_insert_new_candles_ignores_conflicts_and_returns_inserted_count() -> None:
    """Insert uses the DO NOTHING statement and returns rows actually inserted."""
    candles = pd.DataFrame(
        {
            "ts": pd.to_datetime([1_700_000_000_000, 1_700_000_060_000], unit="ms", utc=True),
            "open": [1.0, 1.1],
            "high": [2.0, 2.1],
            "low": [0.5, 0.6],
            "close": [1.5, 1.6],
            "volume": [10.0, 11.0],
        }
    )
    cursor = MagicMock()
    # Only one of the two rows was new; the other hit ON CONFLICT DO NOTHING.
    cursor.rowcount = 1
    conn = _conn_with_cursor(cursor)

    inserted = CandleRepository().insert_new_candles("BTC/USDT", "1m", candles, conn=conn)

    assert inserted == 1
    sql_used = cursor.executemany.call_args.args[0]
    assert sql_used == queries.INSERT_CANDLE_IGNORE
    conn.commit.assert_called_once()
