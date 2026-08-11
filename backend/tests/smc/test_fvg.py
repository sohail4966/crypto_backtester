"""FVG detector tests."""

from __future__ import annotations

from smc.config import SmcConfig
from smc.fvg import detect_fvg
from smc.types import FvgInvalidation, SmcSide
from tests.smc.helpers import ohlcv


def test_bullish_fvg_formation():
    # candle0 high=10, candle2 low=12 → gap 10..12
    df = ohlcv(
        [
            (10, 10.0, 9.0, 9.5),
            (9.5, 11.0, 9.4, 10.5),
            (10.5, 13.0, 12.0, 12.5),
        ]
    )
    events = detect_fvg(df, SmcConfig())
    assert len(events) == 1
    assert events[0].side is SmcSide.BULLISH
    assert events[0].meta["gap_bottom"] == 10.0
    assert events[0].meta["gap_top"] == 12.0


def test_fvg_full_fill_invalidation():
    df = ohlcv(
        [
            (10, 10.0, 9.0, 9.5),
            (9.5, 11.0, 9.4, 10.5),
            (10.5, 13.0, 12.0, 12.5),  # FVG forms
            (12.5, 12.6, 11.5, 11.8),  # touches into gap but not full fill
            (11.8, 11.9, 9.5, 9.8),  # low through gap bottom → full fill
        ]
    )
    events = detect_fvg(df, SmcConfig(fvg_invalidation=FvgInvalidation.FULL_FILL))
    assert events[0].meta["invalidated_at"] == 4


def test_fvg_touch_invalidation_earlier():
    df = ohlcv(
        [
            (10, 10.0, 9.0, 9.5),
            (9.5, 11.0, 9.4, 10.5),
            (10.5, 13.0, 12.0, 12.5),
            (12.5, 12.6, 11.5, 11.8),  # touch near edge
        ]
    )
    touch = detect_fvg(df, SmcConfig(fvg_invalidation=FvgInvalidation.TOUCH))
    full = detect_fvg(df, SmcConfig(fvg_invalidation=FvgInvalidation.FULL_FILL))
    assert touch[0].meta["invalidated_at"] == 3
    assert full[0].meta["invalidated_at"] is None
