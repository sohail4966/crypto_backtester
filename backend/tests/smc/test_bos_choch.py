"""BOS / CHOCH detector tests."""

from __future__ import annotations

from smc.bos import detect_bos_choch
from smc.config import SmcConfig
from smc.pipeline import analyze_smc
from smc.structure_view import structure_for
from smc.types import SmcConcept, SmcSide
from tests.smc.helpers import ohlcv


def _uptrend_then_break() -> tuple:
    """
    Build a series that confirms LH/LL or HH/HL then breaks.

    Pivot 2/2: swing low at 2 (low=8), swing high at 5 (high=12), then more
    structure, then close break.
    """
    df = ohlcv(
        [
            (10, 10.2, 9.8, 10.0),  # 0
            (10, 10.1, 9.7, 9.9),  # 1
            (9.9, 10.0, 8.0, 8.2),  # 2 swing low
            (8.2, 8.5, 8.1, 8.4),  # 3
            (8.4, 8.6, 8.2, 8.5),  # 4 confirms low@2
            (8.5, 12.0, 8.4, 11.5),  # 5 swing high
            (11.5, 11.6, 11.0, 11.2),  # 6
            (11.2, 11.4, 10.8, 11.0),  # 7 confirms high@5
            (11.0, 11.1, 9.0, 9.2),  # 8 swing low (HL if prior low 8)
            (9.2, 9.5, 9.1, 9.4),  # 9
            (9.4, 9.6, 9.2, 9.5),  # 10 confirms low@8
            (9.5, 13.0, 9.4, 12.5),  # 11 swing high HH
            (12.5, 12.6, 12.0, 12.2),  # 12
            (12.2, 12.4, 11.8, 12.0),  # 13 confirms high@11 → uptrend HH+HL
            (12.0, 12.1, 11.9, 12.05),  # 14
            (12.05, 14.0, 12.0, 13.5),  # 15 close > 13.0 → bullish BOS
        ]
    )
    return df, SmcConfig(left_bars=2, right_bars=2)


def test_bullish_bos_in_uptrend():
    df, cfg = _uptrend_then_break()
    structure = structure_for(df, left_bars=cfg.left_bars, right_bars=cfg.right_bars)
    events = detect_bos_choch(df, structure.swings, structure.trend)
    bos = [e for e in events if e.concept is SmcConcept.BOS and e.side is SmcSide.BULLISH]
    assert bos, f"expected bullish BOS, got {events}"
    assert bos[0].index == 15


def test_bearish_choch_against_uptrend():
    df, cfg = _uptrend_then_break()
    # Extend: after uptrend, close below last swing low (9.0 at bar 8)
    base = df.copy()
    more = [
        (13.5, 13.6, 13.4, 13.5),  # 16
        (13.5, 13.6, 8.5, 8.8),  # 17 CHOCH
    ]
    rows = list(
        zip(
            base["open"].tolist() + [r[0] for r in more],
            base["high"].tolist() + [r[1] for r in more],
            base["low"].tolist() + [r[2] for r in more],
            base["close"].tolist() + [r[3] for r in more],
            strict=True,
        )
    )
    df2 = ohlcv(rows)
    structure = structure_for(df2, left_bars=2, right_bars=2)
    events = detect_bos_choch(df2, structure.swings, structure.trend)
    choch = [e for e in events if e.concept is SmcConcept.CHOCH and e.side is SmcSide.BEARISH]
    assert choch, f"expected bearish CHOCH, got {events}"


def test_no_lookahead_before_confirmation():
    df, cfg = _uptrend_then_break()
    result = analyze_smc(df, cfg)
    # Swing high at 5 confirms at 7 — no break events before confirmation usable
    early = [e for e in result.events if e.index < 7 and e.concept in {SmcConcept.BOS, SmcConcept.CHOCH}]
    assert early == []
