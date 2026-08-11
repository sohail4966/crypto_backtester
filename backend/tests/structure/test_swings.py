"""
Tests for symmetric pivot swing detection.
"""

from __future__ import annotations

from structure.swings import detect_swings
from structure.types import SwingKind
from tests.structure.helpers import ohlcv_from_high_low


def test_detects_confirmed_swing_high_and_low() -> None:
    """Clear pivots with left=2/right=2 are confirmed after the right window."""
    # Pivot high at i=2 (10), pivot low at i=7 (1); series long enough to confirm both.
    highs = [1, 2, 10, 2, 1, 3, 4, 5, 4, 3, 2, 2]
    lows = [0.5, 1, 8, 1, 0.5, 2, 3, 1, 2, 1.5, 1, 1]
    df = ohlcv_from_high_low(highs, lows)
    swings = detect_swings(df, left_bars=2, right_bars=2)

    highs_found = [s for s in swings if s.kind is SwingKind.HIGH and s.confirmed]
    lows_found = [s for s in swings if s.kind is SwingKind.LOW and s.confirmed]
    assert any(s.index == 2 and s.price == 10.0 for s in highs_found)
    assert any(s.index == 7 and s.price == 1.0 for s in lows_found)
    high_at_2 = next(s for s in highs_found if s.index == 2)
    assert high_at_2.confirmation_index == 4


def test_plateau_is_not_a_pivot() -> None:
    """Strict inequalities reject equal neighbor highs (D-53)."""
    highs = [1, 2, 5, 5, 1, 2, 3, 4]
    lows = [0.5, 1, 4, 4, 0.5, 1, 2, 3]
    df = ohlcv_from_high_low(highs, lows)
    swings = detect_swings(df, left_bars=2, right_bars=2, confirmed_only=True)
    assert not any(s.kind is SwingKind.HIGH and s.index in {2, 3} for s in swings)


def test_confirmed_only_filters_provisional() -> None:
    """Trailing tip candidates are provisional and dropped when confirmed_only."""
    # Peak near the end cannot get a full right window.
    highs = [1, 2, 3, 4, 9, 4]
    lows = [0.5, 1, 2, 3, 8, 3]
    df = ohlcv_from_high_low(highs, lows)
    all_swings = detect_swings(df, left_bars=2, right_bars=2, confirmed_only=False)
    confirmed = detect_swings(df, left_bars=2, right_bars=2, confirmed_only=True)
    assert any(not s.confirmed for s in all_swings)
    assert all(s.confirmed for s in confirmed)
    assert len(confirmed) < len(all_swings) or any(not s.confirmed for s in all_swings)


def test_empty_frame_returns_empty() -> None:
    """Empty input yields no swings."""
    import pandas as pd

    df = pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
    assert detect_swings(df) == []
