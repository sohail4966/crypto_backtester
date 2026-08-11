"""
Mitigation blocks — first return of price into a still-valid order block zone.
"""

from __future__ import annotations

import pandas as pd

from smc.types import SmcConcept, SmcEvent


def detect_mitigation_blocks(
    df: pd.DataFrame,
    order_blocks: list[SmcEvent],
    breaker_events: list[SmcEvent],
) -> list[SmcEvent]:
    """
    Emit mitigation on first overlap with OB zone before any breaker of that OB.

    Overlap: ``low <= zone_top and high >= zone_bottom``.
    """
    if df.empty or not order_blocks:
        return []

    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)

    events: list[SmcEvent] = []
    for ob in order_blocks:
        if ob.concept is not SmcConcept.ORDER_BLOCK:
            continue
        ob_i = int(ob.meta["ob_index"])
        bottom = float(ob.meta["zone_bottom"])
        top = float(ob.meta["zone_top"])
        start = int(ob.meta.get("visible_from", ob.index)) + 1
        # Scan only while OB is still valid (before any breaker of this OB).
        end = len(high)
        for br in breaker_events:
            if br.meta.get("from_ob_index") == ob_i:
                end = min(end, br.index)
                break

        for i in range(start, end):
            if float(low.iloc[i]) <= top and float(high.iloc[i]) >= bottom:
                events.append(
                    SmcEvent(
                        concept=SmcConcept.MITIGATION_BLOCK,
                        side=ob.side,
                        index=i,
                        ts=stamps[i],
                        price=(bottom + top) / 2.0,
                        meta={
                            "ob_index": ob_i,
                            "zone_bottom": bottom,
                            "zone_top": top,
                        },
                    )
                )
                break
    return events
