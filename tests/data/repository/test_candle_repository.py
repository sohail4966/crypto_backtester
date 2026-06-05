"""
Tests for CandleRepository read metadata using a mocked database cursor.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

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
