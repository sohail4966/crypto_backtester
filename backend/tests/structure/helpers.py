"""
Shared helpers for structure unit tests.
"""

from __future__ import annotations

import pandas as pd


def ohlcv_from_high_low(
    highs: list[float],
    lows: list[float],
    *,
    start: str = "2024-01-01",
    freq: str = "h",
) -> pd.DataFrame:
    """Build a minimal OHLCV frame from high/low series."""
    n = len(highs)
    assert n == len(lows)
    index = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    close = [(h + low) / 2.0 for h, low in zip(highs, lows, strict=True)]
    return pd.DataFrame(
        {
            "ts": index,
            "open": close,
            "high": highs,
            "low": lows,
            "close": close,
            "volume": [1000.0] * n,
        }
    )
