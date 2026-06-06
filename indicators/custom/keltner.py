"""Keltner Channels — EMA middle band with ATR offsets."""

from __future__ import annotations

import pandas as pd

from indicators.talib_wrappers import atr, ema
from indicators.validation import validate_period

DEFAULT_KELTNER_PERIOD = 20
DEFAULT_KELTNER_MULTIPLIER = 2.0


def _keltner_bands(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_KELTNER_PERIOD,
    multiplier: float = DEFAULT_KELTNER_MULTIPLIER,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    validate_period(period, min_val=1, series=close)
    if multiplier <= 0:
        raise ValueError(f"multiplier must be > 0, got {multiplier}")
    middle = ema(close, period=period)
    atr_values = atr(close, high=high, low=low, period=period)
    offset = multiplier * atr_values
    return middle + offset, middle, middle - offset


def keltner_upper(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_KELTNER_PERIOD,
    multiplier: float = DEFAULT_KELTNER_MULTIPLIER,
) -> pd.Series:
    """Keltner Channel upper band (EMA + multiplier × ATR)."""
    upper, _, _ = _keltner_bands(
        close, high=high, low=low, period=period, multiplier=multiplier
    )
    return upper


def keltner_middle(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_KELTNER_PERIOD,
    multiplier: float = DEFAULT_KELTNER_MULTIPLIER,
) -> pd.Series:
    """Keltner Channel middle band (EMA of close)."""
    _, middle, _ = _keltner_bands(
        close, high=high, low=low, period=period, multiplier=multiplier
    )
    return middle


def keltner_lower(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_KELTNER_PERIOD,
    multiplier: float = DEFAULT_KELTNER_MULTIPLIER,
) -> pd.Series:
    """Keltner Channel lower band (EMA − multiplier × ATR)."""
    _, _, lower = _keltner_bands(
        close, high=high, low=low, period=period, multiplier=multiplier
    )
    return lower
