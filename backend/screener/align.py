"""
As-of forward-fill alignment helpers for multi-TF screener conditions (D-106).
"""

from __future__ import annotations

import pandas as pd


def asof_ffill_bool(series: pd.Series, base_ts: pd.Series) -> pd.Series:
    """
    Align a timestamp-indexed boolean Series onto base candle timestamps.

    Forward-fills known values; missing leading values become False (no lookahead).
    """
    base_index = pd.DatetimeIndex(pd.to_datetime(base_ts, utc=True))
    aligned = series.astype(bool).copy()
    if not isinstance(aligned.index, pd.DatetimeIndex):
        aligned.index = pd.DatetimeIndex(pd.to_datetime(aligned.index, utc=True))
    if aligned.index.tz is None:
        aligned.index = aligned.index.tz_localize("UTC")
    else:
        aligned.index = aligned.index.tz_convert("UTC")
    aligned = aligned[~aligned.index.duplicated(keep="last")].sort_index()
    return aligned.reindex(base_index, method="ffill").fillna(False).astype(bool)
