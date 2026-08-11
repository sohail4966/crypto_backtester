"""
Tests for analyze_structure pipeline.
"""

from __future__ import annotations

from structure.pipeline import analyze_structure
from structure.types import SwingKind
from tests.structure.helpers import ohlcv_from_high_low


def test_analyze_structure_end_to_end() -> None:
    """Pipeline returns swings, levels, and an aligned trend Series."""
    highs = [1, 2, 10, 2, 1, 3, 4, 12, 4, 3, 2, 5, 6, 7, 6]
    lows = [0.5, 1, 8, 1, 0.5, 2, 1.0, 10, 2, 1.5, 1.0, 3, 4, 5, 4]
    df = ohlcv_from_high_low(highs, lows)
    result = analyze_structure(df, left_bars=2, right_bars=2)

    assert len(result.swings) >= 2
    assert any(s.kind is SwingKind.HIGH for s in result.swings)
    assert len(result.trend) == len(df)
    assert list(result.trend.index) == list(df["ts"])
    assert isinstance(result.levels.support, list)
    assert isinstance(result.levels.resistance, list)
