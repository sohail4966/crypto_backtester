"""
Tests for StructureContext multi-TF forward-fill.
"""

from __future__ import annotations

import pandas as pd
import pytest

from structure.context import StructureContext
from structure.types import Trend
from tests.structure.helpers import ohlcv_from_high_low


def test_htf_trend_asof_forward_fill_no_lookahead() -> None:
    """Base bars only see HTF trend from HTF timestamps at or before the base ts."""
    # Base: hourly for 8 hours
    base = ohlcv_from_high_low(
        [1, 2, 3, 4, 5, 6, 7, 8],
        [0.5, 1, 2, 3, 4, 5, 6, 7],
        start="2024-01-01 00:00:00",
        freq="h",
    )
    # HTF: 4h bars — craft clear structure so trend becomes defined later
    htf_highs = [1, 2, 10, 2, 1, 3, 4, 12, 4, 3, 2, 5, 6, 11, 6, 5]
    htf_lows = [0.5, 1, 8, 1, 0.5, 2, 1, 10, 2, 1.5, 1, 3, 4, 9, 4, 3]
    htf = ohlcv_from_high_low(
        htf_highs,
        htf_lows,
        start="2024-01-01 00:00:00",
        freq="4h",
    )

    ctx = StructureContext.from_frames(
        "1h",
        base,
        {"4h": htf},
        left_bars=2,
        right_bars=2,
    )
    aligned = ctx.htf_trend_on_base["4h"]
    assert list(aligned.index) == list(base["ts"])
    # First base bar cannot see future HTF trend beyond as-of
    assert aligned.iloc[0] in {Trend.UNDEFINED, Trend.UPTREND, Trend.DOWNTREND, Trend.RANGE}
    # Ensure ffill never pulls a future HTF timestamp's exclusive info incorrectly:
    # value at base_ts equals last HTF trend with htf_ts <= base_ts
    htf_trend = ctx.higher["4h"].trend
    for base_ts, value in aligned.items():
        eligible = htf_trend[htf_trend.index <= base_ts]
        if eligible.empty:
            assert value is Trend.UNDEFINED
        else:
            assert value == eligible.iloc[-1]


def test_empty_htf_raises() -> None:
    """Empty HTF frame fails hard."""
    base = ohlcv_from_high_low([1, 2, 3, 4, 5, 6], [0.5, 1, 2, 3, 4, 5])
    empty = pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
    with pytest.raises(ValueError, match="4h"):
        StructureContext.from_frames("1h", base, {"4h": empty}, left_bars=2, right_bars=2)
