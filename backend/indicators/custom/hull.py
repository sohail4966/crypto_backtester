"""Hull Moving Average — WMA-based smooth moving average."""

from __future__ import annotations

import math

import pandas as pd

from indicators.talib_wrappers import wma
from indicators.validation import validate_period

DEFAULT_HMA_PERIOD = 9


def hma(close: pd.Series, period: int = DEFAULT_HMA_PERIOD) -> pd.Series:
    """
    Hull Moving Average: WMA(2 × WMA(n/2) − WMA(n), sqrt(n)).
    """
    validate_period(period, min_val=2, series=close)
    half_period = max(period // 2, 1)
    sqrt_period = max(int(math.sqrt(period)), 1)
    wma_half = wma(close, period=half_period)
    wma_full = wma(close, period=period)
    raw = 2.0 * wma_half - wma_full
    return wma(raw, period=sqrt_period)
