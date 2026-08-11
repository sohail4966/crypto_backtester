"""
Fair Value Gap (FVG) — three-candle imbalance.

ICT-leaning: bullish FVG when candle1 high < candle3 low; bearish when
candle1 low > candle3 high. Default invalidation is full fill (D-97).
"""

from __future__ import annotations

import pandas as pd

from smc.config import SmcConfig
from smc.types import FvgInvalidation, SmcConcept, SmcEvent, SmcSide


def detect_fvg(df: pd.DataFrame, config: SmcConfig) -> list[SmcEvent]:
    """Detect FVG formation events (named condition fires on formation bar)."""
    n = len(df)
    if n < 3:
        return []

    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)
    events: list[SmcEvent] = []

    for i in range(2, n):
        h0, l0 = float(high.iloc[i - 2]), float(low.iloc[i - 2])
        h2, l2 = float(high.iloc[i]), float(low.iloc[i])

        if h0 < l2:
            bottom, top = h0, l2
            side = SmcSide.BULLISH
        elif l0 > h2:
            bottom, top = h2, l0
            side = SmcSide.BEARISH
        else:
            continue

        mid = (bottom + top) / 2.0
        if mid == 0:
            continue
        gap_pct = (top - bottom) / abs(mid)
        if gap_pct < config.fvg_min_gap_pct:
            continue

        inv_bar = _first_invalidation(
            high=high,
            low=low,
            start=i + 1,
            bottom=bottom,
            top=top,
            side=side,
            mode=config.fvg_invalidation,
        )
        events.append(
            SmcEvent(
                concept=SmcConcept.FVG,
                side=side,
                index=i,
                ts=stamps[i],
                price=mid,
                meta={
                    "gap_bottom": bottom,
                    "gap_top": top,
                    "invalidation": config.fvg_invalidation.value,
                    "invalidated_at": inv_bar,
                },
            )
        )
    return events


def _first_invalidation(
    *,
    high: pd.Series,
    low: pd.Series,
    start: int,
    bottom: float,
    top: float,
    side: SmcSide,
    mode: FvgInvalidation,
) -> int | None:
    """Return first bar index that invalidates the gap, or None."""
    mid = (bottom + top) / 2.0
    for j in range(start, len(high)):
        hj, lj = float(high.iloc[j]), float(low.iloc[j])
        if side is SmcSide.BULLISH:
            if mode is FvgInvalidation.TOUCH and lj <= top:
                return j
            if mode is FvgInvalidation.MIDPOINT and lj <= mid:
                return j
            if mode is FvgInvalidation.FULL_FILL and lj <= bottom:
                return j
        else:
            if mode is FvgInvalidation.TOUCH and hj >= bottom:
                return j
            if mode is FvgInvalidation.MIDPOINT and hj >= mid:
                return j
            if mode is FvgInvalidation.FULL_FILL and hj >= top:
                return j
    return None
