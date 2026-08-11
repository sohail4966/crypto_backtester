"""
Breaker blocks — failed order blocks that flip role after a close-through.
"""

from __future__ import annotations

import pandas as pd

from smc.types import SmcConcept, SmcEvent, SmcSide


def detect_breaker_blocks(df: pd.DataFrame, order_blocks: list[SmcEvent]) -> list[SmcEvent]:
    """
    Emit a breaker when price closes through an order block against its side.

    Bullish OB broken by close < zone_bottom → bearish breaker.
    Bearish OB broken by close > zone_top → bullish breaker.
    """
    if df.empty or not order_blocks:
        return []

    close = df["close"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)
    events: list[SmcEvent] = []

    for ob in order_blocks:
        if ob.concept is not SmcConcept.ORDER_BLOCK:
            continue
        bottom = float(ob.meta["zone_bottom"])
        top = float(ob.meta["zone_top"])
        start = int(ob.meta.get("visible_from", ob.index)) + 1
        for i in range(start, len(close)):
            c = float(close.iloc[i])
            if ob.side is SmcSide.BULLISH and c < bottom:
                events.append(
                    SmcEvent(
                        concept=SmcConcept.BREAKER_BLOCK,
                        side=SmcSide.BEARISH,
                        index=i,
                        ts=stamps[i],
                        price=c,
                        meta={
                            "from_ob_index": ob.meta.get("ob_index"),
                            "zone_bottom": bottom,
                            "zone_top": top,
                        },
                    )
                )
                break
            if ob.side is SmcSide.BEARISH and c > top:
                events.append(
                    SmcEvent(
                        concept=SmcConcept.BREAKER_BLOCK,
                        side=SmcSide.BULLISH,
                        index=i,
                        ts=stamps[i],
                        price=c,
                        meta={
                            "from_ob_index": ob.meta.get("ob_index"),
                            "zone_bottom": bottom,
                            "zone_top": top,
                        },
                    )
                )
                break
    return events
