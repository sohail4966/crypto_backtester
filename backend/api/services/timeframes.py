"""
Supported API candle timeframes.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime

from data.repository.candle_repository import DERIVED_INTERVALS

SUPPORTED_TIMEFRAMES: list[str] = ["1m", *sorted(DERIVED_INTERVALS.keys())]

TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 3 * 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "2h": 2 * 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
    "1w": 7 * 24 * 60 * 60,
    # Approximate only for non-calendar consumers; prefer calendar helpers for 1M (BE-010).
    "1M": 30 * 24 * 60 * 60,
}


def _to_utc_dt(ts: int) -> datetime:
    """Unix seconds → UTC datetime."""
    return datetime.fromtimestamp(ts, tz=UTC)


def month_floor_unix(ts: int) -> int:
    """Return unix seconds of the first moment of the UTC calendar month containing ``ts``."""
    dt = _to_utc_dt(ts)
    return int(datetime(dt.year, dt.month, 1, tzinfo=UTC).timestamp())


def month_ceil_unix(ts: int) -> int:
    """
    Return unix seconds of the first moment of the next UTC calendar month after ``ts``.

    If ``ts`` is exactly on a month boundary, returns ``ts`` (already at ceil).
    """
    dt = _to_utc_dt(ts)
    if dt.day == 1 and dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
        return ts
    year, month = dt.year, dt.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return int(datetime(year, month, 1, tzinfo=UTC).timestamp())


def shift_months_unix(ts: int, months: int) -> int:
    """
    Shift a unix timestamp by ``months`` calendar months in UTC.

    Day-of-month is clamped to the last valid day of the target month
    (e.g. Jan 31 → Feb 28/29).
    """
    dt = _to_utc_dt(ts)
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    shifted = datetime(
        year,
        month,
        day,
        dt.hour,
        dt.minute,
        dt.second,
        dt.microsecond,
        tzinfo=UTC,
    )
    return int(shifted.timestamp())


def shift_unix_by_bars(ts: int, timeframe: str, bars: int) -> int:
    """
    Move a unix timestamp earlier by a number of bars.

    For ``1M``, uses calendar-month math (BE-010).
    """
    validate_timeframe(timeframe)
    if timeframe == "1M":
        return shift_months_unix(ts, -bars)
    return ts - bars * TIMEFRAME_SECONDS[timeframe]


def advance_unix_by_bars(ts: int, timeframe: str, bars: int) -> int:
    """
    Move a unix timestamp later by a number of bars.

    For ``1M``, uses calendar-month math (BE-010).
    """
    validate_timeframe(timeframe)
    if timeframe == "1M":
        return shift_months_unix(ts, bars)
    return ts + bars * TIMEFRAME_SECONDS[timeframe]


def validate_timeframe(timeframe: str) -> None:
    """
    Raise ValueError when timeframe is not supported.

    Args:
        timeframe: Requested candle resolution.

    Raises:
        ValueError: If unsupported.
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        supported = ", ".join(SUPPORTED_TIMEFRAMES)
        raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {supported}")
