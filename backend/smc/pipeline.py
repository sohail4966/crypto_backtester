"""
Single-timeframe SMC analysis pipeline.
"""

from __future__ import annotations

import pandas as pd

from smc.bos import detect_bos_choch
from smc.breaker import detect_breaker_blocks
from smc.config import SmcConfig
from smc.fvg import detect_fvg
from smc.liquidity import detect_liquidity_sweeps
from smc.mitigation import detect_mitigation_blocks
from smc.order_block import detect_order_blocks
from smc.structure_view import event_index, prepare_ohlcv, structure_for
from smc.types import SmcConcept, SmcEvent, SmcResult


def analyze_smc(df: pd.DataFrame, config: SmcConfig | None = None) -> SmcResult:
    """
    Run all SMC detectors on one OHLCV series.

    Args:
        df: Candles with open/high/low/close and ``ts`` or DatetimeIndex.
        config: Optional ``SmcConfig`` (ICT-leaning defaults).

    Returns:
        ``SmcResult`` with combined events ordered by bar index then concept.
    """
    cfg = config or SmcConfig()
    frame = prepare_ohlcv(df)
    if frame.empty:
        return SmcResult(events=[], config=cfg)

    structure = structure_for(frame, left_bars=cfg.left_bars, right_bars=cfg.right_bars)
    bos_choch = detect_bos_choch(frame, structure.swings, structure.trend)
    bos_only = [e for e in bos_choch if e.concept is SmcConcept.BOS]
    fvgs = detect_fvg(frame, cfg)
    sweeps = detect_liquidity_sweeps(frame, structure.swings)
    order_blocks = detect_order_blocks(frame, bos_only, cfg)
    breakers = detect_breaker_blocks(frame, order_blocks)
    mitigations = detect_mitigation_blocks(frame, order_blocks, breakers)

    events: list[SmcEvent] = [
        *bos_choch,
        *fvgs,
        *sweeps,
        *order_blocks,
        *breakers,
        *mitigations,
    ]
    events.sort(key=lambda e: (e.index, e.concept.value, e.side.value))
    return SmcResult(events=events, config=cfg)


def smc_signal_series(
    df: pd.DataFrame,
    concept: str,
    *,
    side: str = "any",
    config: SmcConfig | None = None,
) -> pd.Series:
    """Convenience: boolean Series for one concept from ``analyze_smc``."""
    frame = prepare_ohlcv(df)
    result = analyze_smc(frame, config)
    return result.series_for(event_index(frame), concept, side=side)
