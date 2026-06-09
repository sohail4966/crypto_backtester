"""
Tests for 1m gap detection and reconciliation against data_gaps.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from data.gaps import GapRange, detect_gap_ranges, find_gaps, reconcile_gaps
from data.repository import Gap

MINUTE = timedelta(minutes=1)
T0 = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)


def _minute(index: int) -> datetime:
    """Return the timestamp index minutes after the base time."""
    return T0 + index * MINUTE


def test_detect_gap_ranges_clean_series_returns_empty() -> None:
    """A complete minute series has no gaps."""
    present = [_minute(0), _minute(1), _minute(2)]
    assert detect_gap_ranges(present, _minute(0), _minute(2), "1m") == []


def test_detect_gap_ranges_single_missing_minute() -> None:
    """One missing minute yields a single one-minute range."""
    present = [_minute(0), _minute(2)]
    assert detect_gap_ranges(present, _minute(0), _minute(2), "1m") == [
        GapRange(_minute(1), _minute(1))
    ]


def test_detect_gap_ranges_merges_contiguous_missing() -> None:
    """Adjacent missing minutes merge into one range."""
    present = [_minute(0), _minute(4)]
    assert detect_gap_ranges(present, _minute(0), _minute(4), "1m") == [
        GapRange(_minute(1), _minute(3))
    ]


def test_detect_gap_ranges_separate_gaps() -> None:
    """Non-adjacent missing minutes produce separate ranges."""
    present = [_minute(0), _minute(2), _minute(4)]
    assert detect_gap_ranges(present, _minute(0), _minute(4), "1m") == [
        GapRange(_minute(1), _minute(1)),
        GapRange(_minute(3), _minute(3)),
    ]


def test_detect_gap_ranges_missing_at_boundaries() -> None:
    """Missing candles at the start and end of the window are detected."""
    present = [_minute(2)]
    assert detect_gap_ranges(present, _minute(0), _minute(4), "1m") == [
        GapRange(_minute(0), _minute(1)),
        GapRange(_minute(3), _minute(4)),
    ]


def test_find_gaps_reads_timestamps_from_repository() -> None:
    """find_gaps queries stored timestamps and detects the missing minute."""
    candle_repo = MagicMock()
    candle_repo.find_timestamps.return_value = [_minute(0), _minute(2)]

    ranges = find_gaps("BTC/USDT", "1m", _minute(0), _minute(2), candle_repo=candle_repo)

    assert ranges == [GapRange(_minute(1), _minute(1))]
    candle_repo.find_timestamps.assert_called_once_with(
        "BTC/USDT", "1m", _minute(0).isoformat(), _minute(2).isoformat()
    )


def test_reconcile_gaps_creates_newly_detected_gap() -> None:
    """A detected gap not yet recorded is persisted as a new open gap."""
    candle_repo = MagicMock()
    candle_repo.find_timestamps.return_value = [_minute(0), _minute(2)]
    gap_repo = MagicMock()
    gap_repo.find_open_gaps.return_value = []

    summary = reconcile_gaps(
        "BTC/USDT", "1m", _minute(0), _minute(2), candle_repo=candle_repo, gap_repo=gap_repo
    )

    assert summary.created == 1
    assert summary.resolved == 0
    gap_repo.create_gap.assert_called_once_with("BTC/USDT", "1m", _minute(1), _minute(1))


def test_reconcile_gaps_does_not_duplicate_existing_open_gap() -> None:
    """An already-open gap with the same bounds is not inserted again."""
    candle_repo = MagicMock()
    candle_repo.find_timestamps.return_value = [_minute(0), _minute(2)]
    gap_repo = MagicMock()
    gap_repo.find_open_gaps.return_value = [
        Gap(1, "BTC/USDT", "1m", _minute(1), _minute(1), "open", 0)
    ]

    summary = reconcile_gaps(
        "BTC/USDT", "1m", _minute(0), _minute(2), candle_repo=candle_repo, gap_repo=gap_repo
    )

    assert summary.created == 0
    gap_repo.create_gap.assert_not_called()
    # The gap is still missing, so it must not be resolved.
    gap_repo.mark_gap_resolved.assert_not_called()


def test_reconcile_gaps_resolves_filled_gap() -> None:
    """An open gap whose candles now all exist is marked resolved."""
    candle_repo = MagicMock()
    candle_repo.find_timestamps.return_value = [_minute(0), _minute(1), _minute(2)]
    gap_repo = MagicMock()
    gap_repo.find_open_gaps.return_value = [
        Gap(7, "BTC/USDT", "1m", _minute(1), _minute(1), "open", 0)
    ]

    summary = reconcile_gaps(
        "BTC/USDT", "1m", _minute(0), _minute(2), candle_repo=candle_repo, gap_repo=gap_repo
    )

    assert summary.resolved == 1
    gap_repo.mark_gap_resolved.assert_called_once_with(7)


def test_reconcile_gaps_ignores_gap_outside_window() -> None:
    """An open gap outside the audited range is neither resolved nor recreated."""
    candle_repo = MagicMock()
    candle_repo.find_timestamps.return_value = [_minute(0), _minute(1), _minute(2)]
    gap_repo = MagicMock()
    gap_repo.find_open_gaps.return_value = [
        Gap(9, "BTC/USDT", "1m", _minute(10), _minute(10), "open", 0)
    ]

    summary = reconcile_gaps(
        "BTC/USDT", "1m", _minute(0), _minute(2), candle_repo=candle_repo, gap_repo=gap_repo
    )

    assert summary.resolved == 0
    gap_repo.mark_gap_resolved.assert_not_called()
