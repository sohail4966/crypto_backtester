"""Donchian Channels — rolling high/low envelope."""

from __future__ import annotations

import pandas as pd

from indicators.validation import validate_period

DEFAULT_DONCHIAN_PERIOD = 20


def _donchian_bands(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_DONCHIAN_PERIOD,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    validate_period(period, min_val=1, series=close)
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2.0
    return upper, middle, lower


def donchian_upper(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_DONCHIAN_PERIOD,
) -> pd.Series:
    """Donchian upper band (rolling highest high)."""
    upper, _, _ = _donchian_bands(close, high=high, low=low, period=period)
    return upper.astype(float)


def donchian_middle(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_DONCHIAN_PERIOD,
) -> pd.Series:
    """Donchian middle band (average of upper and lower)."""
    _, middle, _ = _donchian_bands(close, high=high, low=low, period=period)
    return middle.astype(float)


def donchian_lower(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_DONCHIAN_PERIOD,
) -> pd.Series:
    """Donchian lower band (rolling lowest low)."""
    _, _, lower = _donchian_bands(close, high=high, low=low, period=period)
    return lower.astype(float)
