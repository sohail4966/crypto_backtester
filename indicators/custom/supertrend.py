"""SuperTrend — ATR-based trend line with direction flips."""

from __future__ import annotations

import numpy as np
import pandas as pd

from indicators.talib_wrappers import atr
from indicators.validation import validate_period

DEFAULT_SUPERTREND_PERIOD = 10
DEFAULT_SUPERTREND_MULTIPLIER = 3.0


def supertrend(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_SUPERTREND_PERIOD,
    multiplier: float = DEFAULT_SUPERTREND_MULTIPLIER,
) -> pd.Series:
    """
    SuperTrend line via ATR bands and direction flips.

    Uses HL2 ± multiplier × ATR; flips between upper and lower bands on close cross.
    """
    validate_period(period, min_val=1, series=close)
    if multiplier <= 0:
        raise ValueError(f"multiplier must be > 0, got {multiplier}")

    atr_values = atr(close, high=high, low=low, period=period)
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + multiplier * atr_values
    basic_lower = hl2 - multiplier * atr_values

    n = len(close)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    supertrend_values = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)

    close_arr = close.to_numpy(dtype=float)
    basic_upper_arr = basic_upper.to_numpy(dtype=float)
    basic_lower_arr = basic_lower.to_numpy(dtype=float)

    for i in range(n):
        if np.isnan(basic_upper_arr[i]) or np.isnan(basic_lower_arr[i]):
            continue
        if i == 0:
            final_upper[i] = basic_upper_arr[i]
            final_lower[i] = basic_lower_arr[i]
            supertrend_values[i] = final_lower[i]
            continue

        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        if np.isnan(prev_upper) or np.isnan(prev_lower):
            final_upper[i] = basic_upper_arr[i]
            final_lower[i] = basic_lower_arr[i]
        else:
            final_upper[i] = (
                basic_upper_arr[i]
                if basic_upper_arr[i] < prev_upper or close_arr[i - 1] > prev_upper
                else prev_upper
            )
            final_lower[i] = (
                basic_lower_arr[i]
                if basic_lower_arr[i] > prev_lower or close_arr[i - 1] < prev_lower
                else prev_lower
            )

        if direction[i - 1] == 1:
            direction[i] = -1 if close_arr[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if close_arr[i] > final_upper[i] else -1

        supertrend_values[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    return pd.Series(supertrend_values, index=close.index, dtype=float)
