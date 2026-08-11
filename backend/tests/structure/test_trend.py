"""
Tests for event-driven trend classification.
"""

from __future__ import annotations

import pandas as pd

from structure.trend import classify_trend
from structure.types import SwingKind, SwingLabel, SwingPoint, Trend
from tests.structure.helpers import ohlcv_from_high_low


def _sw(
    index: int,
    price: float,
    kind: SwingKind,
    label: SwingLabel,
    confirmation_index: int,
) -> SwingPoint:
    """Build a confirmed labeled swing."""
    return SwingPoint(
        index=index,
        ts=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=index),
        price=price,
        kind=kind,
        label=label,
        confirmed=True,
        confirmation_index=confirmation_index,
    )


def test_uptrend_hh_hl_forward_fill() -> None:
    """HH+HL becomes uptrend at confirmation and forward-fills."""
    df = ohlcv_from_high_low([1] * 20, [0.5] * 20)
    swings = [
        _sw(2, 100.0, SwingKind.HIGH, SwingLabel.FIRST, 4),
        _sw(5, 90.0, SwingKind.LOW, SwingLabel.FIRST, 7),
        _sw(8, 110.0, SwingKind.HIGH, SwingLabel.HH, 10),
        _sw(11, 95.0, SwingKind.LOW, SwingLabel.HL, 13),
    ]
    trend = classify_trend(df, swings)
    assert trend.iloc[12] is Trend.UNDEFINED or trend.iloc[12] == Trend.UNDEFINED
    # After low confirms at 13 with 2 highs + 2 lows → uptrend
    assert trend.iloc[13] is Trend.UPTREND
    assert trend.iloc[-1] is Trend.UPTREND
    assert all(v is Trend.UNDEFINED for v in trend.iloc[:4])


def test_downtrend_lh_ll() -> None:
    """LH+LL classifies as downtrend."""
    df = ohlcv_from_high_low([1] * 20, [0.5] * 20)
    swings = [
        _sw(2, 110.0, SwingKind.HIGH, SwingLabel.FIRST, 4),
        _sw(5, 100.0, SwingKind.LOW, SwingLabel.FIRST, 7),
        _sw(8, 105.0, SwingKind.HIGH, SwingLabel.LH, 10),
        _sw(11, 90.0, SwingKind.LOW, SwingLabel.LL, 13),
    ]
    trend = classify_trend(df, swings)
    assert trend.iloc[13] is Trend.DOWNTREND


def test_eqh_yields_range() -> None:
    """EQH on latest high forces range even with HL lows."""
    df = ohlcv_from_high_low([1] * 20, [0.5] * 20)
    swings = [
        _sw(2, 100.0, SwingKind.HIGH, SwingLabel.FIRST, 4),
        _sw(5, 90.0, SwingKind.LOW, SwingLabel.FIRST, 7),
        _sw(8, 100.1, SwingKind.HIGH, SwingLabel.EQH, 10),
        _sw(11, 95.0, SwingKind.LOW, SwingLabel.HL, 13),
    ]
    trend = classify_trend(df, swings)
    assert trend.iloc[13] is Trend.RANGE


def test_mixed_structure_is_range() -> None:
    """HH + LL is mixed → range."""
    df = ohlcv_from_high_low([1] * 20, [0.5] * 20)
    swings = [
        _sw(2, 100.0, SwingKind.HIGH, SwingLabel.FIRST, 4),
        _sw(5, 95.0, SwingKind.LOW, SwingLabel.FIRST, 7),
        _sw(8, 110.0, SwingKind.HIGH, SwingLabel.HH, 10),
        _sw(11, 90.0, SwingKind.LOW, SwingLabel.LL, 13),
    ]
    trend = classify_trend(df, swings)
    assert trend.iloc[13] is Trend.RANGE


def test_insufficient_swings_undefined() -> None:
    """Fewer than two highs and two lows stays undefined."""
    df = ohlcv_from_high_low([1] * 10, [0.5] * 10)
    swings = [
        _sw(2, 100.0, SwingKind.HIGH, SwingLabel.FIRST, 4),
        _sw(5, 90.0, SwingKind.LOW, SwingLabel.FIRST, 7),
    ]
    trend = classify_trend(df, swings)
    assert all(v is Trend.UNDEFINED for v in trend)
