"""
Single-frame pattern analysis pipeline (candles + classical + divergence).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from patterns.candles import detect_candlestick_patterns
from patterns.classical import detect_classical_patterns
from patterns.divergence import detect_divergences
from patterns.series import hits_to_signals
from patterns.types import PatternFamily, PatternHit, PatternResult
from structure.labels import DEFAULT_EQ_TOLERANCE_PCT
from structure.ohlcv import candle_timestamps
from structure.pipeline import analyze_structure
from structure.swings import DEFAULT_LEFT_BARS, DEFAULT_RIGHT_BARS


def analyze_patterns(
    df: pd.DataFrame,
    *,
    families: Sequence[str] | Sequence[PatternFamily] = (
        PatternFamily.CANDLE,
        PatternFamily.CLASSICAL,
        PatternFamily.DIVERGENCE,
    ),
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
    tolerance_pct: float = DEFAULT_EQ_TOLERANCE_PCT,
) -> PatternResult:
    """
    Run selected pattern families on one OHLCV series.

    Classical and divergence paths use ``analyze_structure(..., confirmed_only=True)``.
    Boolean Series are sparse True only on each hit's confirmation bar.
    """
    fams = {PatternFamily(f) if not isinstance(f, PatternFamily) else f for f in families}
    hits: list[PatternHit] = []

    if PatternFamily.CANDLE in fams:
        hits.extend(detect_candlestick_patterns(df))

    need_structure = PatternFamily.CLASSICAL in fams or PatternFamily.DIVERGENCE in fams
    swings = []
    if need_structure:
        structure = analyze_structure(
            df,
            left_bars=left_bars,
            right_bars=right_bars,
            tolerance_pct=tolerance_pct,
            confirmed_only=True,
        )
        swings = structure.swings

    if PatternFamily.CLASSICAL in fams:
        hits.extend(detect_classical_patterns(df, swings))

    if PatternFamily.DIVERGENCE in fams:
        hits.extend(detect_divergences(df, swings))

    hits.sort(key=lambda h: (h.end_index, h.family.value, h.name.value))
    if df.empty:
        index = pd.DatetimeIndex([], tz="UTC")
    else:
        index = candle_timestamps(df)
    signals = hits_to_signals(hits, index)
    return PatternResult(hits=hits, signals=signals)
