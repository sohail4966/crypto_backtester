"""Historical volatility, volatility rank, and volatility oscillator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from indicators.talib_wrappers import atr, stddev
from indicators.validation import validate_period

DEFAULT_HISTVOL_PERIOD = 20
DEFAULT_HISTVOL_ANNUALIZATION = 252.0
DEFAULT_VOLRANK_PERIOD = 100
DEFAULT_VOLOSCILLATOR_SHORT = 5
DEFAULT_VOLOSCILLATOR_LONG = 10


def histvol(
    close: pd.Series,
    *,
    period: int = DEFAULT_HISTVOL_PERIOD,
    annualization: float = DEFAULT_HISTVOL_ANNUALIZATION,
) -> pd.Series:
    """
    Historical volatility: rolling std of log returns, annualized.

    HV = stdev(ln(close/close_prev), period) × sqrt(annualization).
    """
    validate_period(period, min_val=2, series=close)
    if annualization <= 0:
        raise ValueError(f"annualization must be > 0, got {annualization}")
    log_returns = np.log(close / close.shift(1))
    rolling_std = log_returns.rolling(window=period, min_periods=period).std()
    return (rolling_std * np.sqrt(annualization)).astype(float)


def volrank(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_VOLRANK_PERIOD,
    atr_period: int = 14,
) -> pd.Series:
    """
    Volatility rank: percentile rank of ATR within a rolling lookback window.

    Returns value in [0, 100] where 100 is the highest ATR in the window.
    """
    validate_period(period, min_val=2, series=close)
    validate_period(atr_period, min_val=1, series=close)
    atr_values = atr(close, high=high, low=low, period=atr_period)

    def _percentile_rank(window: pd.Series) -> float:
        current = window.iloc[-1]
        if np.isnan(current):
            return float("nan")
        return float((window <= current).sum() / len(window) * 100.0)

    return atr_values.rolling(window=period, min_periods=period).apply(_percentile_rank, raw=False)


def volatility_oscillator(
    close: pd.Series,
    *,
    short_period: int = DEFAULT_VOLOSCILLATOR_SHORT,
    long_period: int = DEFAULT_VOLOSCILLATOR_LONG,
) -> pd.Series:
    """
    Volatility Oscillator (TV-aligned): 100 × (STDDEV_short / STDDEV_long).

    Uses TA-Lib STDDEV on close; ratio × 100. Returns NaN when long STDDEV is zero.
    """
    validate_period(short_period, min_val=2, series=close)
    validate_period(long_period, min_val=2, series=close)
    if short_period >= long_period:
        raise ValueError("short_period must be less than long_period")
    short_std = stddev(close, period=short_period)
    long_std = stddev(close, period=long_period)
    result = pd.Series(float("nan"), index=close.index, dtype=float)
    valid = long_std != 0
    result[valid] = 100.0 * (short_std[valid] / long_std[valid])
    return result
