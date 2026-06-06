"""Ichimoku Cloud — TV-style layout (D-36 defaults: 9, 26, 52, displacement 26)."""

from __future__ import annotations

import pandas as pd

from indicators.validation import validate_period

DEFAULT_ICHIMOKU_TENKAN = 9
DEFAULT_ICHIMOKU_KIJUN = 26
DEFAULT_ICHIMOKU_SENKOU_B = 52
DEFAULT_ICHIMOKU_DISPLACEMENT = 26


def _midpoint(high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    validate_period(period, min_val=1, series=high)
    rolling_high = high.rolling(window=period, min_periods=period).max()
    rolling_low = low.rolling(window=period, min_periods=period).min()
    return ((rolling_high + rolling_low) / 2.0).astype(float)


def ichimoku_tenkan(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> pd.Series:
    """Ichimoku conversion line (Tenkan-sen)."""
    _ = (kijun, senkou_b, displacement)
    return _midpoint(high, low, tenkan)


def ichimoku_kijun(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> pd.Series:
    """Ichimoku base line (Kijun-sen)."""
    _ = (tenkan, senkou_b, displacement)
    return _midpoint(high, low, kijun)


def ichimoku_senkou_a(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> pd.Series:
    """Ichimoku leading span A, shifted forward by displacement."""
    _ = senkou_b
    tenkan_line = _midpoint(high, low, tenkan)
    kijun_line = _midpoint(high, low, kijun)
    return ((tenkan_line + kijun_line) / 2.0).shift(displacement).astype(float)


def ichimoku_senkou_b(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> pd.Series:
    """Ichimoku leading span B, shifted forward by displacement."""
    _ = (tenkan, kijun)
    return _midpoint(high, low, senkou_b).shift(displacement).astype(float)


def ichimoku_chikou(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> pd.Series:
    """Ichimoku lagging span (close shifted back by displacement)."""
    _ = (high, low, tenkan, kijun, senkou_b)
    return close.shift(-displacement).astype(float)
