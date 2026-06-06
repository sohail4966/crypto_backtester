"""Chandelier Exit — ATR-based trailing stop."""

from __future__ import annotations

import pandas as pd

from indicators.talib_wrappers import atr
from indicators.validation import validate_period

DEFAULT_CHANDELIER_PERIOD = 22
DEFAULT_CHANDELIER_MULTIPLIER = 3.0


def chandelier(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_CHANDELIER_PERIOD,
    multiplier: float = DEFAULT_CHANDELIER_MULTIPLIER,
) -> pd.Series:
    """
    Chandelier Exit (long): highest high over period minus multiplier × ATR.
    """
    validate_period(period, min_val=1, series=close)
    if multiplier <= 0:
        raise ValueError(f"multiplier must be > 0, got {multiplier}")
    highest_high = high.rolling(window=period, min_periods=period).max()
    atr_values = atr(close, high=high, low=low, period=period)
    return (highest_high - multiplier * atr_values).astype(float)
