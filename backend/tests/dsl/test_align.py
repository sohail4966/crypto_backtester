"""
Tests for look-ahead-safe multi-timeframe alignment.
"""

from __future__ import annotations

import pandas as pd

from dsl.align import align_series_to_base, resample_ohlcv


def _hourly_candles(n: int = 48) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = [100.0 + (i % 10) for i in range(n)]
    return pd.DataFrame(
        {
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def test_resample_ohlcv_hourly_to_daily() -> None:
    hourly = _hourly_candles(48)
    daily = resample_ohlcv(hourly, "1d")
    assert len(daily) >= 2
    assert list(daily.columns) == ["open", "high", "low", "close", "volume"]


def test_align_series_no_lookahead() -> None:
    """As-of ffill never uses a future HTF open after the base timestamp."""
    hourly = _hourly_candles(48)
    day_open = pd.Timestamp("2024-01-02", tz="UTC")
    htf = pd.Series([True], index=[day_open])
    aligned = align_series_to_base(htf, hourly.index, "1d")
    # Before the HTF open → False
    assert aligned.loc[pd.Timestamp("2024-01-01 12:00", tz="UTC")] == False  # noqa: E712
    # At/after HTF open → True
    assert aligned.loc[pd.Timestamp("2024-01-02 00:00", tz="UTC")] == True  # noqa: E712


def test_align_completed_only_delays_until_close() -> None:
    """completed_only waits until HTF bar close before exposing the value."""
    hourly = _hourly_candles(48)
    day_open = pd.Timestamp("2024-01-01", tz="UTC")
    htf = pd.Series([True], index=[day_open])
    aligned = align_series_to_base(htf, hourly.index, "1d", completed_only=True)
    assert aligned.loc[pd.Timestamp("2024-01-01 12:00", tz="UTC")] == False  # noqa: E712
    assert aligned.loc[pd.Timestamp("2024-01-02 00:00", tz="UTC")] == True  # noqa: E712
