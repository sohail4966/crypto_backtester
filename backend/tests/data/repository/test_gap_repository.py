"""
Tests for GapRepository CRUD using a mocked database cursor.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from data.repository import queries
from data.repository.gap_repository import Gap, GapRepository

START = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
END = datetime(2024, 1, 1, 0, 5, tzinfo=UTC)


def _conn_with_cursor(cursor: MagicMock) -> MagicMock:
    """Build a mock connection whose cursor() context manager yields the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn


def test_create_gap_inserts_open_row_and_returns_id() -> None:
    """A new gap is inserted as 'open' and its generated id is returned and committed."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (42,)
    conn = _conn_with_cursor(cursor)

    gap_id = GapRepository().create_gap("BTC/USDT", "1m", START, END, conn=conn)

    assert gap_id == 42
    cursor.execute.assert_called_once_with(queries.INSERT_GAP, ("BTC/USDT", "1m", START, END))
    conn.commit.assert_called_once()


def test_find_open_gaps_maps_rows_to_gap_objects() -> None:
    """Returned rows are mapped to Gap dataclasses in order."""
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (1, "BTC/USDT", "1m", START, END, "open", 0),
    ]
    conn = _conn_with_cursor(cursor)

    gaps = GapRepository().find_open_gaps("BTC/USDT", "1m", conn=conn)

    assert gaps == [Gap(1, "BTC/USDT", "1m", START, END, "open", 0)]
    cursor.execute.assert_called_once_with(queries.SELECT_OPEN_GAPS, ("BTC/USDT", "1m"))


def test_find_open_gaps_returns_empty_when_none_open() -> None:
    """No open gaps yields an empty list, not an error."""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = _conn_with_cursor(cursor)

    assert GapRepository().find_open_gaps("BTC/USDT", "1m", conn=conn) == []


def test_mark_gap_resolved_executes_resolve_and_commits() -> None:
    """Resolving a gap runs the resolve statement for the id and commits."""
    cursor = MagicMock()
    conn = _conn_with_cursor(cursor)

    GapRepository().mark_gap_resolved(7, conn=conn)

    cursor.execute.assert_called_once_with(queries.RESOLVE_GAP, (7,))
    conn.commit.assert_called_once()


def test_record_gap_retry_increments_with_error_and_commits() -> None:
    """A retry records the error message and the gap id, then commits."""
    cursor = MagicMock()
    conn = _conn_with_cursor(cursor)

    GapRepository().record_gap_retry(7, last_error="timeout", conn=conn)

    cursor.execute.assert_called_once_with(queries.RECORD_GAP_RETRY, ("timeout", 7))
    conn.commit.assert_called_once()
