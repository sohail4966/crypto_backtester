"""
Indicator functions for computing technical analysis values from OHLCV data.

All functions are pure: they take a pandas Series and return a pandas Series.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_RSI_PERIOD = 14


def sma(close: pd.Series, period: int) -> pd.Series:
    """
    Compute a simple moving average of closing prices.

    Args:
        close: Closing price series.
        period: Rolling window length in bars.

    Returns:
        SMA values; first (period - 1) rows are NaN.

    Raises:
        ValueError: If period is less than 1 or the series is shorter than period.
    """
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    if len(close) < period:
        raise ValueError(f"series length {len(close)} is shorter than period {period}")
    return close.rolling(window=period, min_periods=period).mean()


def _wilder_rma(values: pd.Series, period: int) -> pd.Series:
    """
    Apply Wilder's recursive moving average (RMA).

    Args:
        values: Input series (e.g. gains or losses).
        period: Smoothing period.

    Returns:
        RMA series; values before index period - 1 are NaN.
    """
    result = pd.Series(index=values.index, dtype=float)
    if len(values) < period:
        return result

    # Seed with SMA of the first `period` values, then apply Wilder's recurrence.
    result.iloc[period - 1] = values.iloc[:period].mean()
    for i in range(period, len(values)):
        result.iloc[i] = (result.iloc[i - 1] * (period - 1) + values.iloc[i]) / period
    return result


def rsi(close: pd.Series, period: int = DEFAULT_RSI_PERIOD) -> pd.Series:
    """
    Compute RSI using Wilder's smoothing method (matches TradingView output).

    Args:
        close: Closing price series, indexed by datetime.
        period: Lookback period. Default is 14.

    Returns:
        RSI values as a float Series in the range [0, 100].
        First (period) values are NaN until the RMA seed is established.

    Raises:
        ValueError: If period is less than 2 or greater than len(close).
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if len(close) < period:
        raise ValueError(f"series length {len(close)} is shorter than period {period}")

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder's RMA (not EMA) — must match TradingView for sanity checks (D-13).
    avg_gain = _wilder_rma(gain, period)
    avg_loss = _wilder_rma(loss, period)

    rs = avg_gain / avg_loss
    out = 100 - (100 / (1 + rs))
    # No losses in the window implies RSI = 100 (standard convention).
    out[avg_loss == 0] = 100.0
    return out
