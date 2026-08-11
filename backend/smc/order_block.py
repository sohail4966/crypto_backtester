"""
Order Blocks — last opposing candle before a BOS impulse.

ICT-leaning: bullish OB = last down-close candle before bullish BOS;
bearish OB = last up-close candle before bearish BOS.

The named-condition event fires at ``visible_from`` (the BOS bar) so consumers
do not see the OB before it is knowable (no lookahead).
"""

from __future__ import annotations

import pandas as pd

from smc.config import SmcConfig
from smc.types import SmcConcept, SmcEvent, SmcSide


def detect_order_blocks(
    df: pd.DataFrame,
    bos_events: list[SmcEvent],
    config: SmcConfig,
) -> list[SmcEvent]:
    """Derive order blocks from BOS events."""
    if df.empty or not bos_events:
        return []

    open_ = df["open"].astype(float).reset_index(drop=True)
    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    close = df["close"].astype(float).reset_index(drop=True)
    stamps = pd.DatetimeIndex(df["ts"]) if "ts" in df.columns else pd.DatetimeIndex(df.index)
    events: list[SmcEvent] = []

    for bos in bos_events:
        if bos.concept is not SmcConcept.BOS:
            continue
        ob_i = _find_opposing_candle(open_, close, bos.index, bos.side)
        if ob_i is None:
            continue
        if config.ob_use_wick_range:
            zone_bottom = float(low.iloc[ob_i])
            zone_top = float(high.iloc[ob_i])
        else:
            zone_bottom = min(float(open_.iloc[ob_i]), float(close.iloc[ob_i]))
            zone_top = max(float(open_.iloc[ob_i]), float(close.iloc[ob_i]))

        events.append(
            SmcEvent(
                concept=SmcConcept.ORDER_BLOCK,
                side=bos.side,
                index=bos.index,  # visible when BOS prints
                ts=stamps[bos.index],
                price=(zone_bottom + zone_top) / 2.0,
                meta={
                    "ob_index": ob_i,
                    "visible_from": bos.index,
                    "zone_bottom": zone_bottom,
                    "zone_top": zone_top,
                    "bos_index": bos.index,
                },
            )
        )
    return events


def _find_opposing_candle(
    open_: pd.Series,
    close: pd.Series,
    bos_index: int,
    side: SmcSide,
) -> int | None:
    """Scan backward from bar before BOS for the last opposing body candle."""
    for i in range(bos_index - 1, -1, -1):
        o, c = float(open_.iloc[i]), float(close.iloc[i])
        if side is SmcSide.BULLISH and c < o:
            return i
        if side is SmcSide.BEARISH and c > o:
            return i
    return None
