"""
OHLCV helpers shared by structure modules.
"""

from __future__ import annotations

import pandas as pd


def require_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate OHLC columns and normalize ``ts`` to UTC when present.

    Args:
        df: Candle frame with ``high`` / ``low`` and ``ts`` or a DatetimeIndex.

    Returns:
        The original frame, or a copy with ``ts`` parsed to UTC.

    Raises:
        ValueError: If required columns or timestamps are missing.
    """
    required = {"high", "low"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"candles missing columns: {sorted(missing)}")
    if df.empty:
        return df
    if "ts" in df.columns:
        out = df.copy()
        out["ts"] = pd.to_datetime(out["ts"], utc=True)
        return out
    if isinstance(df.index, pd.DatetimeIndex):
        out = df.copy()
        out.index = pd.DatetimeIndex(out.index, tz="UTC")
        return out
    raise ValueError("candles require a ts column or DatetimeIndex")


def candle_timestamps(df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Return bar timestamps as a UTC DatetimeIndex.

    Args:
        df: Candle frame with ``ts`` or a DatetimeIndex.

    Returns:
        UTC DatetimeIndex aligned to rows.
    """
    if "ts" in df.columns:
        return pd.DatetimeIndex(pd.to_datetime(df["ts"], utc=True))
    return pd.DatetimeIndex(df.index, tz="UTC")
