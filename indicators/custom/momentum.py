"""Momentum oscillators — TSI, Awesome Oscillator, Qstick."""

from __future__ import annotations

import pandas as pd

from indicators.talib_wrappers import ema, sma
from indicators.validation import validate_period

DEFAULT_TSI_LONG = 25
DEFAULT_TSI_SHORT = 13
DEFAULT_AO_FAST = 5
DEFAULT_AO_SLOW = 34
DEFAULT_QSTICK_PERIOD = 8


def _double_smooth(series: pd.Series, long_period: int, short_period: int) -> pd.Series:
    return ema(ema(series, period=long_period), period=short_period)


def tsi(
    close: pd.Series,
    *,
    long_period: int = DEFAULT_TSI_LONG,
    short_period: int = DEFAULT_TSI_SHORT,
) -> pd.Series:
    """
    True Strength Index: double-smoothed momentum oscillator.

    TSI = 100 × EMA(EMA(Δclose, long), short) / EMA(EMA(|Δclose|, long), short).
    """
    validate_period(long_period, min_val=1, series=close)
    validate_period(short_period, min_val=1, series=close)
    diff = close.diff()
    smoothed = _double_smooth(diff, long_period, short_period)
    smoothed_abs = _double_smooth(diff.abs(), long_period, short_period)
    result = pd.Series(float("nan"), index=close.index, dtype=float)
    valid = smoothed_abs != 0
    result[valid] = 100.0 * (smoothed[valid] / smoothed_abs[valid])
    return result


def ao(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    fast_period: int = DEFAULT_AO_FAST,
    slow_period: int = DEFAULT_AO_SLOW,
) -> pd.Series:
    """
    Awesome Oscillator: SMA(median price, fast) − SMA(median price, slow).

    Median price = (high + low) / 2.
    """
    validate_period(fast_period, min_val=1, series=close)
    validate_period(slow_period, min_val=1, series=close)
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
    median = (high + low) / 2.0
    return (sma(median, period=fast_period) - sma(median, period=slow_period)).astype(float)


def qstick(
    close: pd.Series,
    *,
    open: pd.Series,
    period: int = DEFAULT_QSTICK_PERIOD,
) -> pd.Series:
    """Qstick: EMA of (close − open)."""
    validate_period(period, min_val=1, series=close)
    if len(open) != len(close):
        raise ValueError("open series length must match close series length")
    return ema(close - open, period=period)
