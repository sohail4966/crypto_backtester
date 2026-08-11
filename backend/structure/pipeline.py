"""
Single-timeframe structure analysis pipeline.
"""

from __future__ import annotations

import pandas as pd

from structure.labels import DEFAULT_EQ_TOLERANCE_PCT, label_swings
from structure.levels import DEFAULT_LEVEL_COUNT, structure_levels
from structure.swings import DEFAULT_LEFT_BARS, DEFAULT_RIGHT_BARS, detect_swings
from structure.trend import classify_trend
from structure.types import StructureResult


def analyze_structure(
    df: pd.DataFrame,
    *,
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
    tolerance_pct: float = DEFAULT_EQ_TOLERANCE_PCT,
    k: int = DEFAULT_LEVEL_COUNT,
    confirmed_only: bool = False,
) -> StructureResult:
    """
    Run swing detection, labeling, S/R, and trend classification on one series.

    Args:
        df: OHLCV candles.
        left_bars: Pivot left width. Default 5.
        right_bars: Pivot right width / confirmation lag. Default 5.
        tolerance_pct: EQH/EQL relative tolerance. Default 0.15%.
        k: Number of S/R levels. Default 3.
        confirmed_only: When True, drop provisional swings from the result list
            (levels/trend already ignore provisional).

    Returns:
        ``StructureResult`` with swings, levels, and trend Series.
    """
    swings = detect_swings(
        df,
        left_bars=left_bars,
        right_bars=right_bars,
        confirmed_only=confirmed_only,
    )
    labeled = label_swings(swings, tolerance_pct=tolerance_pct)
    levels = structure_levels(labeled, k=k)
    trend = classify_trend(df, labeled)
    return StructureResult(swings=labeled, levels=levels, trend=trend)
