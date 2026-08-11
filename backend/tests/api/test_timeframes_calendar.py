"""Tests for calendar-month timeframe helpers (BE-010)."""

from __future__ import annotations

from datetime import UTC, datetime

from api.services.timeframes import (
    advance_unix_by_bars,
    month_floor_unix,
    shift_months_unix,
    shift_unix_by_bars,
)


def test_month_floor_and_jan31_to_feb() -> None:
    jan31 = int(datetime(2024, 1, 31, 12, 0, tzinfo=UTC).timestamp())
    assert month_floor_unix(jan31) == int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    feb = shift_months_unix(jan31, 1)
    # 2024 is leap year → Feb 29
    assert datetime.fromtimestamp(feb, tz=UTC).month == 2
    assert datetime.fromtimestamp(feb, tz=UTC).day == 29


def test_shift_unix_by_bars_1m_uses_calendar() -> None:
    start = int(datetime(2024, 3, 15, tzinfo=UTC).timestamp())
    earlier = shift_unix_by_bars(start, "1M", 1)
    later = advance_unix_by_bars(start, "1M", 1)
    assert datetime.fromtimestamp(earlier, tz=UTC) == datetime(2024, 2, 15, tzinfo=UTC)
    assert datetime.fromtimestamp(later, tz=UTC) == datetime(2024, 4, 15, tzinfo=UTC)
