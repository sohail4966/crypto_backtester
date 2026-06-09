"""Volume indexes and volume oscillator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from indicators.talib_wrappers import sma
from indicators.validation import validate_period

DEFAULT_VOLOSC_SHORT = 5
DEFAULT_VOLOSC_LONG = 10
DEFAULT_NVI_START = 1000.0


def volosc(
    close: pd.Series,
    *,
    volume: pd.Series,
    short_period: int = DEFAULT_VOLOSC_SHORT,
    long_period: int = DEFAULT_VOLOSC_LONG,
) -> pd.Series:
    """
    Volume Oscillator: ((short MA volume − long MA volume) / long MA volume) × 100.
    """
    validate_period(short_period, min_val=1, series=close)
    validate_period(long_period, min_val=1, series=close)
    if short_period >= long_period:
        raise ValueError("short_period must be less than long_period")
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    short_ma = sma(volume, period=short_period)
    long_ma = sma(volume, period=long_period)
    result = pd.Series(float("nan"), index=close.index, dtype=float)
    valid = long_ma != 0
    result[valid] = ((short_ma[valid] - long_ma[valid]) / long_ma[valid]) * 100.0
    return result


def _volume_index(
    close: pd.Series,
    volume: pd.Series,
    *,
    positive: bool,
    start: float = DEFAULT_NVI_START,
) -> pd.Series:
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    values = close.to_numpy(dtype=float)
    volumes = volume.to_numpy(dtype=float)
    index_values = [float("nan")] * len(close)
    if len(close) == 0:
        return pd.Series(index_values, index=close.index, dtype=float)

    index_values[0] = start
    for i in range(1, len(close)):
        prev_index = index_values[i - 1]
        if np.isnan(prev_index):
            index_values[i] = float("nan")
            continue
        volume_changed = volumes[i] > volumes[i - 1] if positive else volumes[i] < volumes[i - 1]
        if volume_changed and values[i - 1] != 0:
            pct_change = (values[i] - values[i - 1]) / values[i - 1]
            index_values[i] = prev_index * (1.0 + pct_change)
        else:
            index_values[i] = prev_index

    return pd.Series(index_values, index=close.index, dtype=float)


def nvi(close: pd.Series, *, volume: pd.Series, start: float = DEFAULT_NVI_START) -> pd.Series:
    """
    Negative Volume Index: updates when volume decreases from prior bar.
    """
    return _volume_index(close, volume, positive=False, start=start)


def pvi(close: pd.Series, *, volume: pd.Series, start: float = DEFAULT_NVI_START) -> pd.Series:
    """
    Positive Volume Index: updates when volume increases from prior bar.
    """
    return _volume_index(close, volume, positive=True, start=start)
