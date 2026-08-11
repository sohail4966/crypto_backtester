"""
Break of Structure (BOS) and Change of Character (CHOCH).

ICT-leaning default: a **close** beyond a confirmed swing high/low.
- BOS — break in the direction of the current structure trend (continuation)
- CHOCH — break against the current trend (character change / potential reversal)

When trend is range/undefined, the first close break sets local bias (CHOCH);
later same-direction breaks are BOS.
"""

from __future__ import annotations

import pandas as pd

from smc.structure_view import last_swing, trend_at, usable_swings
from smc.types import SmcConcept, SmcEvent, SmcSide
from structure.types import SwingKind, SwingPoint, Trend


def detect_bos_choch(
    df: pd.DataFrame,
    swings: list[SwingPoint],
    trend: pd.Series,
) -> list[SmcEvent]:
    """
    Detect BOS and CHOCH events on ``df``.

    Each swing level is consumed after its first close break so the same level
    does not re-fire.
    """
    n = len(df)
    if n == 0:
        return []

    close = df["close"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)
    events: list[SmcEvent] = []
    broken_highs: set[int] = set()
    broken_lows: set[int] = set()
    local_bias: Trend | None = None

    for i in range(n):
        known = usable_swings(swings, i)
        high = last_swing(known, SwingKind.HIGH)
        low = last_swing(known, SwingKind.LOW)
        state = trend_at(trend, i)
        bias = state if state in (Trend.UPTREND, Trend.DOWNTREND) else local_bias

        if high is not None and high.index not in broken_highs and float(close.iloc[i]) > high.price:
            side = SmcSide.BULLISH
            concept = _classify_break(bias, bullish=True)
            events.append(
                SmcEvent(
                    concept=concept,
                    side=side,
                    index=i,
                    ts=stamps[i],
                    price=float(close.iloc[i]),
                    meta={"swing_index": high.index, "level": high.price},
                )
            )
            broken_highs.add(high.index)
            if concept is SmcConcept.CHOCH:
                local_bias = Trend.UPTREND
            elif bias is None:
                local_bias = Trend.UPTREND

        if low is not None and low.index not in broken_lows and float(close.iloc[i]) < low.price:
            side = SmcSide.BEARISH
            concept = _classify_break(bias, bullish=False)
            events.append(
                SmcEvent(
                    concept=concept,
                    side=side,
                    index=i,
                    ts=stamps[i],
                    price=float(close.iloc[i]),
                    meta={"swing_index": low.index, "level": low.price},
                )
            )
            broken_lows.add(low.index)
            if concept is SmcConcept.CHOCH:
                local_bias = Trend.DOWNTREND
            elif bias is None:
                local_bias = Trend.DOWNTREND

    return events


def _classify_break(bias: Trend | None, *, bullish: bool) -> SmcConcept:
    """Map trend bias + break direction to BOS or CHOCH."""
    if bias is Trend.UPTREND:
        return SmcConcept.BOS if bullish else SmcConcept.CHOCH
    if bias is Trend.DOWNTREND:
        return SmcConcept.BOS if not bullish else SmcConcept.CHOCH
    # range / undefined / no local bias yet → first break is CHOCH
    return SmcConcept.CHOCH
