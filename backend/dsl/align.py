"""
Higher-timeframe resampling and look-ahead-safe alignment.
"""

from __future__ import annotations

import pandas as pd

from data.fetcher import TIMEFRAME_MS, timeframe_to_ms
from exceptions import InvalidSignalError


_OHLCV_AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}


def _ensure_datetime_index(candles: pd.DataFrame) -> pd.DataFrame:
    """Return a frame indexed by UTC timestamps (open labels)."""
    if isinstance(candles.index, pd.DatetimeIndex):
        frame = candles.copy()
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        return frame
    if "ts" not in candles.columns:
        raise InvalidSignalError("candles require a DatetimeIndex or 'ts' column")
    frame = candles.copy()
    ts = pd.to_datetime(frame["ts"], utc=True)
    frame = frame.drop(columns=["ts"])
    frame.index = ts
    return frame


def resample_ohlcv(candles: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Aggregate OHLCV to a higher timeframe labeled by bar open time.

    Args:
        candles: Base OHLCV (DatetimeIndex or ``ts`` column).
        timeframe: Target resolution (must be in ``TIMEFRAME_MS``).

    Returns:
        Resampled OHLCV with DatetimeIndex.
    """
    if timeframe not in TIMEFRAME_MS:
        raise InvalidSignalError(f"Unsupported timeframe: {timeframe!r}")
    frame = _ensure_datetime_index(candles)
    cols = [c for c in _OHLCV_AGG if c in frame.columns]
    if "close" not in cols:
        raise InvalidSignalError("candles missing required 'close' column")
    rule = _pandas_rule(timeframe)
    out = frame[cols].resample(rule, label="left", closed="left").agg(
        {c: _OHLCV_AGG[c] for c in cols}
    )
    return out.dropna(subset=["close"])


def _pandas_rule(timeframe: str) -> str:
    """Map platform TF strings to pandas offset aliases."""
    mapping = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "1d": "1D",
        "1w": "7D",
        "1M": "30D",
    }
    if timeframe not in mapping:
        raise InvalidSignalError(f"Unsupported timeframe: {timeframe!r}")
    return mapping[timeframe]


def align_series_to_base(
    htf_series: pd.Series,
    base_index: pd.DatetimeIndex,
    timeframe: str,
    *,
    completed_only: bool = False,
) -> pd.Series:
    """
    Align an HTF series to a base index without using future HTF bars.

    Default (D-106): as-of forward-fill on HTF **open** labels — a base bar at
    time ``t`` sees the last HTF bar with ``open <= t``.

    When ``completed_only=True`` (stricter Phase 9 option): HTF values become
    available only after the HTF bar closes (``open + timeframe_duration``).

    Args:
        htf_series: Series indexed by HTF open timestamps.
        base_index: Base (lower TF) open timestamps.
        timeframe: HTF resolution string.
        completed_only: If True, delay availability until HTF close.

    Returns:
        Boolean/float Series aligned to ``base_index``.
    """
    if htf_series.empty:
        return pd.Series(False, index=base_index)
    idx = pd.DatetimeIndex(htf_series.index)
    if completed_only:
        duration = pd.Timedelta(milliseconds=timeframe_to_ms(timeframe))
        idx = idx + duration
    avail = pd.Series(htf_series.to_numpy(), index=idx)
    avail = avail[~avail.index.duplicated(keep="last")].sort_index()
    aligned = avail.reindex(base_index, method="ffill")
    # Bars before the first known HTF bar stay False (not NaN).
    if pd.api.types.is_bool_dtype(htf_series.dtype) or htf_series.dtype == object:
        return aligned.fillna(False).astype(bool)
    return aligned.fillna(False)
