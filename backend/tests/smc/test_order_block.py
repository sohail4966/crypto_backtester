"""Order block, breaker, and mitigation tests."""

from __future__ import annotations

from smc.bos import detect_bos_choch
from smc.breaker import detect_breaker_blocks
from smc.config import SmcConfig
from smc.mitigation import detect_mitigation_blocks
from smc.order_block import detect_order_blocks
from smc.structure_view import structure_for
from smc.types import SmcConcept, SmcSide
from tests.smc.helpers import ohlcv


def _bos_with_ob_frame():
    """Series ending in bullish BOS with a clear prior down candle."""
    df = ohlcv(
        [
            (10, 10.2, 9.8, 10.0),
            (10, 10.1, 9.7, 9.9),
            (9.9, 10.0, 8.0, 8.2),  # 2 swing low
            (8.2, 8.5, 8.1, 8.4),
            (8.4, 8.6, 8.2, 8.5),  # 4 confirm low
            (8.5, 12.0, 8.4, 11.5),  # 5 swing high
            (11.5, 11.6, 11.0, 11.2),
            (11.2, 11.4, 10.8, 11.0),  # 7 confirm high
            (11.0, 11.1, 9.0, 9.2),  # 8 swing low HL
            (9.2, 9.5, 9.1, 9.4),
            (9.4, 9.6, 9.2, 9.5),  # 10 confirm low
            (9.5, 13.0, 9.4, 12.5),  # 11 swing high HH
            (12.5, 12.6, 12.0, 12.2),
            (12.2, 12.4, 11.8, 12.0),  # 13 confirm → uptrend
            (12.0, 12.2, 11.5, 11.6),  # 14 down candle = OB candidate
            (11.6, 14.0, 11.5, 13.8),  # 15 bullish BOS close > 13
        ]
    )
    return df, SmcConfig(left_bars=2, right_bars=2)


def test_order_block_visible_on_bos_bar():
    df, cfg = _bos_with_ob_frame()
    structure = structure_for(df, left_bars=2, right_bars=2)
    bos_events = detect_bos_choch(df, structure.swings, structure.trend)
    bos_only = [e for e in bos_events if e.concept is SmcConcept.BOS]
    obs = detect_order_blocks(df, bos_only, cfg)
    assert obs, f"expected OB from {bos_only}"
    ob = obs[0]
    assert ob.side is SmcSide.BULLISH
    assert ob.index == 15  # visible_from = BOS bar
    assert ob.meta["ob_index"] == 14
    assert ob.meta["zone_bottom"] == 11.6
    assert ob.meta["zone_top"] == 12.0


def test_mitigation_before_breaker():
    df, cfg = _bos_with_ob_frame()
    # Continue: return into OB zone then later break it
    rows = list(
        zip(
            df["open"].tolist()
            + [13.8, 12.5],
            df["high"].tolist() + [13.9, 12.6],
            df["low"].tolist() + [11.7, 10.0],  # 16 overlaps OB; 17 closes through
            df["close"].tolist() + [12.0, 10.5],
            strict=True,
        )
    )
    df2 = ohlcv(rows)
    structure = structure_for(df2, left_bars=2, right_bars=2)
    bos_events = detect_bos_choch(df2, structure.swings, structure.trend)
    bos_only = [e for e in bos_events if e.concept is SmcConcept.BOS]
    obs = detect_order_blocks(df2, bos_only, cfg)
    breakers = detect_breaker_blocks(df2, obs)
    mitigations = detect_mitigation_blocks(df2, obs, breakers)
    assert mitigations and mitigations[0].index == 16
    assert breakers and breakers[0].index == 17
    assert breakers[0].side is SmcSide.BEARISH
