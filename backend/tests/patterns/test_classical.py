"""
Tests for classical chart patterns (5b) using explicit swing points.
"""

from __future__ import annotations

import pandas as pd

from patterns.classical import detect_classical_patterns
from patterns.types import PatternName
from structure.types import SwingKind, SwingLabel, SwingPoint
from tests.patterns.helpers import candle, ohlcv


def _sw(
    index: int,
    price: float,
    kind: SwingKind,
    *,
    ts: pd.Timestamp | None = None,
) -> SwingPoint:
    stamp = ts or pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=index)
    return SwingPoint(
        index=index,
        ts=stamp,
        price=price,
        kind=kind,
        label=SwingLabel.FIRST,
        confirmed=True,
        confirmation_index=index + 1,
    )


def test_double_top():
    # highs at 10 equal, neck low 8, then close below 8
    rows = [candle(9, 9.5, 8.5, 9)] * 25
    rows[5] = candle(9.5, 10.0, 9.0, 9.8)
    rows[10] = candle(9.0, 9.2, 8.0, 8.2)
    rows[15] = candle(9.5, 10.05, 9.0, 9.7)
    rows[18] = candle(8.5, 8.6, 7.5, 7.6)  # breakout close
    df = ohlcv(rows)
    swings = [
        _sw(5, 10.0, SwingKind.HIGH),
        _sw(10, 8.0, SwingKind.LOW),
        _sw(15, 10.05, SwingKind.HIGH),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.DOUBLE_TOP and h.direction == "bearish" for h in hits)
    hit = next(h for h in hits if h.name == PatternName.DOUBLE_TOP)
    assert hit.end_index == 18
    assert "neckline" in hit.levels


def test_double_bottom():
    rows = [candle(10, 10.5, 9.5, 10)] * 25
    rows[5] = candle(10, 10.2, 9.0, 9.2)
    rows[10] = candle(9.5, 11.0, 9.4, 10.8)
    rows[15] = candle(10, 10.2, 9.05, 9.3)
    rows[18] = candle(10.5, 11.5, 10.4, 11.4)
    df = ohlcv(rows)
    swings = [
        _sw(5, 9.0, SwingKind.LOW),
        _sw(10, 11.0, SwingKind.HIGH),
        _sw(15, 9.05, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.DOUBLE_BOTTOM for h in hits)


def test_head_and_shoulders():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[20] = candle(9, 9.2, 8.0, 8.1)  # breakout
    df = ohlcv(rows)
    swings = [
        _sw(4, 12.0, SwingKind.HIGH),
        _sw(7, 10.0, SwingKind.LOW),
        _sw(10, 14.0, SwingKind.HIGH),
        _sw(13, 10.2, SwingKind.LOW),
        _sw(16, 12.1, SwingKind.HIGH),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.HEAD_AND_SHOULDERS for h in hits)


def test_inv_head_and_shoulders():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[20] = candle(11, 12.5, 10.9, 12.4)
    df = ohlcv(rows)
    swings = [
        _sw(4, 8.0, SwingKind.LOW),
        _sw(7, 10.0, SwingKind.HIGH),
        _sw(10, 6.0, SwingKind.LOW),
        _sw(13, 9.8, SwingKind.HIGH),
        _sw(16, 8.1, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.INV_HEAD_AND_SHOULDERS for h in hits)


def test_ascending_triangle():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[22] = candle(11, 12.0, 10.9, 11.9)  # break above ~11
    df = ohlcv(rows)
    swings = [
        _sw(5, 11.0, SwingKind.HIGH),
        _sw(8, 9.0, SwingKind.LOW),
        _sw(12, 11.02, SwingKind.HIGH),
        _sw(15, 9.5, SwingKind.LOW),
        _sw(18, 11.01, SwingKind.HIGH),
        _sw(20, 9.9, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.ASC_TRIANGLE for h in hits)


def test_descending_triangle():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[22] = candle(9, 9.1, 8.0, 8.1)
    df = ohlcv(rows)
    swings = [
        _sw(5, 11.0, SwingKind.HIGH),
        _sw(8, 9.0, SwingKind.LOW),
        _sw(12, 10.5, SwingKind.HIGH),
        _sw(15, 9.02, SwingKind.LOW),
        _sw(18, 10.0, SwingKind.HIGH),
        _sw(20, 9.01, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.DESC_TRIANGLE for h in hits)


def test_sym_triangle():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[22] = candle(11, 12.0, 10.9, 11.8)
    df = ohlcv(rows)
    swings = [
        _sw(5, 12.0, SwingKind.HIGH),
        _sw(8, 8.0, SwingKind.LOW),
        _sw(12, 11.0, SwingKind.HIGH),
        _sw(15, 8.5, SwingKind.LOW),
        _sw(18, 10.2, SwingKind.HIGH),
        _sw(20, 9.0, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.SYM_TRIANGLE for h in hits)


def test_bull_flag():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[18] = candle(12, 13.5, 11.9, 13.4)
    df = ohlcv(rows)
    swings = [
        _sw(2, 10.0, SwingKind.LOW),
        _sw(6, 13.0, SwingKind.HIGH),  # impulse +30%
        _sw(9, 12.5, SwingKind.LOW),
        _sw(12, 12.8, SwingKind.HIGH),
        _sw(15, 12.4, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name in {PatternName.BULL_FLAG, PatternName.PENNANT} for h in hits)


def test_bear_flag():
    rows = [candle(13, 13.5, 12.5, 13)] * 30
    rows[18] = candle(11, 11.1, 9.5, 9.6)
    df = ohlcv(rows)
    swings = [
        _sw(2, 13.0, SwingKind.HIGH),
        _sw(6, 10.0, SwingKind.LOW),
        _sw(9, 10.5, SwingKind.HIGH),
        _sw(12, 10.2, SwingKind.LOW),
        _sw(15, 10.4, SwingKind.HIGH),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name in {PatternName.BEAR_FLAG, PatternName.PENNANT} for h in hits)


def test_rising_wedge():
    rows = [candle(10, 10.5, 9.5, 10)] * 30
    rows[22] = candle(10, 10.2, 9.0, 9.1)
    df = ohlcv(rows)
    swings = [
        _sw(5, 10.0, SwingKind.HIGH),
        _sw(8, 8.0, SwingKind.LOW),
        _sw(12, 11.0, SwingKind.HIGH),
        _sw(15, 9.5, SwingKind.LOW),
        _sw(18, 11.5, SwingKind.HIGH),
        _sw(20, 10.5, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.RISING_WEDGE for h in hits)


def test_falling_wedge():
    rows = [candle(12, 12.5, 11.5, 12)] * 30
    rows[22] = candle(11, 12.5, 10.9, 12.4)
    df = ohlcv(rows)
    swings = [
        _sw(5, 14.0, SwingKind.HIGH),
        _sw(8, 12.0, SwingKind.LOW),
        _sw(12, 13.0, SwingKind.HIGH),
        _sw(15, 11.0, SwingKind.LOW),
        _sw(18, 12.2, SwingKind.HIGH),
        _sw(20, 10.5, SwingKind.LOW),
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.FALLING_WEDGE for h in hits)


def test_cup_and_handle():
    rows = [candle(10, 10.5, 9.5, 10)] * 40
    rows[30] = candle(11, 12.5, 10.9, 12.4)
    df = ohlcv(rows)
    swings = [
        _sw(5, 10.0, SwingKind.LOW),
        _sw(10, 12.0, SwingKind.HIGH),
        _sw(15, 8.0, SwingKind.LOW),  # cup
        _sw(20, 11.8, SwingKind.HIGH),
        _sw(22, 10.1, SwingKind.LOW),  # right rim ~ left
        _sw(25, 11.5, SwingKind.HIGH),  # handle high
        _sw(27, 10.8, SwingKind.LOW),  # handle low
    ]
    hits = detect_classical_patterns(df, swings)
    assert any(h.name == PatternName.CUP_AND_HANDLE for h in hits)
