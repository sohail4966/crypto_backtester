"""
Event-driven trend classification from confirmed swing structure (D-56, D-66).
"""

from __future__ import annotations

import pandas as pd

from structure.ohlcv import candle_timestamps
from structure.types import SwingKind, SwingLabel, SwingPoint, Trend


def _trend_from_latest_labels(
    latest_high: SwingLabel | None,
    latest_low: SwingLabel | None,
    high_count: int,
    low_count: int,
) -> Trend:
    """Map latest same-kind labels to a Trend state."""
    if high_count < 2 or low_count < 2:
        return Trend.UNDEFINED
    if latest_high is None or latest_low is None:
        return Trend.UNDEFINED
    if latest_high in {SwingLabel.EQH, SwingLabel.FIRST} or latest_low in {
        SwingLabel.EQL,
        SwingLabel.FIRST,
    }:
        # FIRST should not appear once count >= 2, but treat defensively as undefined/range.
        if latest_high is SwingLabel.FIRST or latest_low is SwingLabel.FIRST:
            return Trend.UNDEFINED
        return Trend.RANGE
    if latest_high is SwingLabel.HH and latest_low is SwingLabel.HL:
        return Trend.UPTREND
    if latest_high is SwingLabel.LH and latest_low is SwingLabel.LL:
        return Trend.DOWNTREND
    return Trend.RANGE


def classify_trend(df: pd.DataFrame, swings: list[SwingPoint]) -> pd.Series:
    """
    Classify structure trend as a Series aligned to candle timestamps.

    Trend is recomputed only when a newly confirmed swing becomes available
    (at ``confirmation_index``), then forward-filled until the next event.

    Args:
        df: OHLCV candles with ``ts`` or a DatetimeIndex.
        swings: Labeled swings (provisional ignored for state updates).

    Returns:
        ``pd.Series`` of ``Trend`` values indexed by UTC timestamps.
    """
    if df.empty:
        return pd.Series(dtype=object)

    stamps = candle_timestamps(df)
    index = pd.DatetimeIndex(stamps)
    values = pd.Series(Trend.UNDEFINED, index=index, dtype=object)

    confirmed = [s for s in swings if s.confirmed and s.confirmation_index is not None]
    if not confirmed:
        return values

    # Events ordered by confirmation bar (when the swing becomes known).
    events = sorted(confirmed, key=lambda s: (s.confirmation_index, s.index))

    known: list[SwingPoint] = []
    event_states: list[tuple[int, Trend]] = []

    for swing in events:
        known.append(swing)
        highs = [s for s in known if s.kind is SwingKind.HIGH]
        lows = [s for s in known if s.kind is SwingKind.LOW]
        latest_high = highs[-1].label if highs else None
        latest_low = lows[-1].label if lows else None
        state = _trend_from_latest_labels(latest_high, latest_low, len(highs), len(lows))
        assert swing.confirmation_index is not None
        event_states.append((swing.confirmation_index, state))

    # Apply events in order; later events overwrite from their confirmation bar onward.
    for conf_i, state in event_states:
        if conf_i < 0 or conf_i >= len(values):
            continue
        values.iloc[conf_i:] = state

    return values
