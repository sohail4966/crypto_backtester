"""Classic pivot points with D-35 session boundaries."""

from __future__ import annotations

import pandas as pd


def _is_daily_timeframe(index: pd.DatetimeIndex) -> bool:
    """True when bars are spaced at roughly one day or more (1d timeframe)."""
    if len(index) < 2:
        return False
    median_delta = index.to_series().diff().median()
    return bool(median_delta >= pd.Timedelta(hours=23))


def _prior_session_hlc(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Prior session H/L/C per D-35.

    Intraday: prior UTC calendar day aggregate.
    Daily (1d): prior bar values.
    """
    index = close.index
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("pivot points require a DatetimeIndex on close")

    if _is_daily_timeframe(index):
        return high.shift(1), low.shift(1), close.shift(1)

    session_key = index.normalize()
    daily = pd.DataFrame({"high": high, "low": low, "close": close}, index=session_key)
    daily_hlc = daily.groupby(level=0).agg({"high": "max", "low": "min", "close": "last"})
    prior = daily_hlc.shift(1)
    mapped = prior.reindex(session_key)
    return (
        pd.Series(mapped["high"].to_numpy(), index=index, dtype=float),
        pd.Series(mapped["low"].to_numpy(), index=index, dtype=float),
        pd.Series(mapped["close"].to_numpy(), index=index, dtype=float),
    )


def _pivot_levels(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, pd.Series]:
    prior_high, prior_low, prior_close = _prior_session_hlc(high, low, close)
    pivot = (prior_high + prior_low + prior_close) / 3.0
    range_hl = prior_high - prior_low
    return {
        "PIVOT_P": pivot.astype(float),
        "PIVOT_R1": (2.0 * pivot - prior_low).astype(float),
        "PIVOT_S1": (2.0 * pivot - prior_high).astype(float),
        "PIVOT_R2": (pivot + range_hl).astype(float),
        "PIVOT_S2": (pivot - range_hl).astype(float),
        "PIVOT_R3": (prior_high + 2.0 * (pivot - prior_low)).astype(float),
        "PIVOT_S3": (prior_low - 2.0 * (prior_high - pivot)).astype(float),
    }


def pivot_p(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """Classic pivot point (P) from prior session H/L/C."""
    return _pivot_levels(high, low, close)["PIVOT_P"]


def pivot_r1(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """First resistance (R1)."""
    return _pivot_levels(high, low, close)["PIVOT_R1"]


def pivot_r2(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """Second resistance (R2)."""
    return _pivot_levels(high, low, close)["PIVOT_R2"]


def pivot_r3(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """Third resistance (R3)."""
    return _pivot_levels(high, low, close)["PIVOT_R3"]


def pivot_s1(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """First support (S1)."""
    return _pivot_levels(high, low, close)["PIVOT_S1"]


def pivot_s2(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """Second support (S2)."""
    return _pivot_levels(high, low, close)["PIVOT_S2"]


def pivot_s3(close: pd.Series, *, high: pd.Series, low: pd.Series) -> pd.Series:
    """Third support (S3)."""
    return _pivot_levels(high, low, close)["PIVOT_S3"]
