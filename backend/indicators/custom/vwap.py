"""VWAP — rolling and UTC session variants (D-29)."""

from __future__ import annotations

import pandas as pd

from indicators.validation import validate_period

DEFAULT_VWAP_PERIOD = 14


def vwap(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    period: int = DEFAULT_VWAP_PERIOD,
    variant: str = "rolling",
) -> pd.Series:
    """
    Volume Weighted Average Price.

    variant=rolling (default): rolling VWAP over `period` bars using typical price.
    variant=session: cumulative VWAP reset at each UTC calendar day.
    """
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    if variant not in {"rolling", "session"}:
        raise ValueError("variant must be 'rolling' or 'session'")

    typical_price = (high + low + close) / 3.0
    pv = typical_price * volume

    if variant == "session":
        if not isinstance(close.index, pd.DatetimeIndex):
            raise ValueError("session VWAP requires a DatetimeIndex on close")
        session_key = close.index.normalize()
        cum_pv = pv.groupby(session_key).cumsum()
        cum_vol = volume.groupby(session_key).cumsum()
        result = cum_pv / cum_vol.replace(0, float("nan"))
        return result.astype(float)

    validate_period(period, min_val=1, series=close)
    rolling_pv = pv.rolling(window=period, min_periods=period).sum()
    rolling_vol = volume.rolling(window=period, min_periods=period).sum()
    return (rolling_pv / rolling_vol).astype(float)
