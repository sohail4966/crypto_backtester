"""Liquidity sweep tests."""

from __future__ import annotations

from smc.liquidity import detect_liquidity_sweeps
from smc.structure_view import structure_for
from smc.types import SmcSide
from tests.smc.helpers import ohlcv


def test_bearish_liquidity_sweep_wick():
    df = ohlcv(
        [
            (10, 10.2, 9.8, 10.0),
            (10, 10.1, 9.7, 9.9),
            (9.9, 10.0, 8.0, 8.2),  # 2 low
            (8.2, 8.5, 8.1, 8.4),
            (8.4, 8.6, 8.2, 8.5),  # 4 confirm low
            (8.5, 12.0, 8.4, 11.5),  # 5 high
            (11.5, 11.6, 11.0, 11.2),
            (11.2, 11.4, 10.8, 11.0),  # 7 confirm high@5 level=12
            (11.0, 12.5, 10.9, 11.2),  # 8 wick > 12, close < 12 → sweep
        ]
    )
    structure = structure_for(df, left_bars=2, right_bars=2)
    events = detect_liquidity_sweeps(df, structure.swings)
    assert events
    assert events[0].side is SmcSide.BEARISH
    assert events[0].index == 8
