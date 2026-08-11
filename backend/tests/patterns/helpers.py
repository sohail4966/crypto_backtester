"""
Shared helpers for pattern unit tests.
"""

from __future__ import annotations

import pandas as pd


def ohlcv(
    rows: list[tuple[float, float, float, float]],
    *,
    start: str = "2024-01-01",
    freq: str = "h",
) -> pd.DataFrame:
    """
    Build OHLCV from (open, high, low, close) tuples.
    """
    n = len(rows)
    index = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    if n == 0:
        return pd.DataFrame(
            {
                "ts": index,
                "open": pd.Series(dtype=float),
                "high": pd.Series(dtype=float),
                "low": pd.Series(dtype=float),
                "close": pd.Series(dtype=float),
                "volume": pd.Series(dtype=float),
            }
        )
    opens, highs, lows, closes = zip(*rows, strict=True)
    return pd.DataFrame(
        {
            "ts": index,
            "open": list(opens),
            "high": list(highs),
            "low": list(lows),
            "close": list(closes),
            "volume": [1000.0] * n,
        }
    )


def candle(o: float, h: float, low: float, c: float) -> tuple[float, float, float, float]:
    assert h >= max(o, c) and low <= min(o, c)
    return (o, h, low, c)
