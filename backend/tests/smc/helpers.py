"""
Shared helpers for SMC unit tests.
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

    Args:
        rows: Per-bar OHLC tuples.
        start: First timestamp.
        freq: Pandas offset alias.
    """
    n = len(rows)
    index = pd.date_range(start, periods=n, freq=freq, tz="UTC")
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


def flat_then_impulse() -> pd.DataFrame:
    """
    Compact series with clear pivots under left=2, right=2.

    Layout (bar index):
      0-1: base
      2: swing low candidate region
      ...
    Constructed so a swing low and swing high confirm, then a close break.
    """
    # highs/lows crafted for pivot 2/2
    return ohlcv(
        [
            (10, 10.5, 9.5, 10),  # 0
            (10, 10.4, 9.6, 10),  # 1
            (10, 10.3, 9.0, 9.2),  # 2 low pivot candidate (low=9.0)
            (9.2, 9.5, 9.1, 9.4),  # 3
            (9.4, 9.6, 9.2, 9.5),  # 4 — confirms low at 2 (right=2)
            (9.5, 11.0, 9.4, 10.8),  # 5 high pivot candidate
            (10.8, 10.9, 10.5, 10.6),  # 6
            (10.6, 10.7, 10.4, 10.5),  # 7 — confirms high at 5
            (10.5, 10.6, 10.3, 10.4),  # 8
            (10.4, 12.0, 10.3, 11.8),  # 9 close breaks above swing high 11.0 → CHOCH/BOS
            (11.8, 12.1, 11.5, 11.9),  # 10
            (11.9, 11.95, 11.0, 11.1),  # 11 down candle (potential OB later)
            (11.1, 13.5, 11.0, 13.2),  # 12 impulse / possible BOS continuation
        ]
    )
