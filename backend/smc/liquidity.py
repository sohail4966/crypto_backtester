"""
Liquidity sweeps — wick beyond a confirmed swing, close back inside (stop hunt).
"""

from __future__ import annotations

import pandas as pd

from smc.structure_view import last_swing, usable_swings
from smc.types import SmcConcept, SmcEvent, SmcSide
from structure.types import SwingKind, SwingPoint


def detect_liquidity_sweeps(df: pd.DataFrame, swings: list[SwingPoint]) -> list[SmcEvent]:
    """Detect same-bar liquidity sweeps of confirmed swing highs/lows."""
    n = len(df)
    if n == 0:
        return []

    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    close = df["close"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)
    events: list[SmcEvent] = []
    swept_highs: set[int] = set()
    swept_lows: set[int] = set()

    for i in range(n):
        known = usable_swings(swings, i)
        swing_high = last_swing(known, SwingKind.HIGH)
        swing_low = last_swing(known, SwingKind.LOW)

        if (
            swing_high is not None
            and swing_high.index not in swept_highs
            and float(high.iloc[i]) > swing_high.price
            and float(close.iloc[i]) < swing_high.price
        ):
            events.append(
                SmcEvent(
                    concept=SmcConcept.LIQUIDITY_SWEEP,
                    side=SmcSide.BEARISH,
                    index=i,
                    ts=stamps[i],
                    price=float(high.iloc[i]),
                    meta={"swing_index": swing_high.index, "level": swing_high.price},
                )
            )
            swept_highs.add(swing_high.index)

        if (
            swing_low is not None
            and swing_low.index not in swept_lows
            and float(low.iloc[i]) < swing_low.price
            and float(close.iloc[i]) > swing_low.price
        ):
            events.append(
                SmcEvent(
                    concept=SmcConcept.LIQUIDITY_SWEEP,
                    side=SmcSide.BULLISH,
                    index=i,
                    ts=stamps[i],
                    price=float(low.iloc[i]),
                    meta={"swing_index": swing_low.index, "level": swing_low.price},
                )
            )
            swept_lows.add(swing_low.index)

    return events
