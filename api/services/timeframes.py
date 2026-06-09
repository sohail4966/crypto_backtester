"""
Supported API candle timeframes.
"""

from __future__ import annotations

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
    # Approximate calendar month for warmup bar shifting (not exact bucket size).
    "1M": 30 * 24 * 60 * 60,
}


def shift_unix_by_bars(ts: int, timeframe: str, bars: int) -> int:
    """
    Move a unix timestamp earlier by a number of bars.

    Args:
        ts: Unix seconds UTC.
        timeframe: Candle resolution.
        bars: Number of bars to subtract.

    Returns:
        Earlier unix timestamp.
    """
    validate_timeframe(timeframe)
    return ts - bars * TIMEFRAME_SECONDS[timeframe]


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
