"""
Tests for divergence detection (5c).
"""

from __future__ import annotations

import pandas as pd
import pytest

from patterns.divergence import detect_divergences
from patterns.types import PatternName
from structure.types import SwingKind, SwingLabel, SwingPoint
from tests.patterns.helpers import candle, ohlcv


def _sw(index: int, price: float, kind: SwingKind) -> SwingPoint:
    return SwingPoint(
        index=index,
        ts=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=index),
        price=price,
        kind=kind,
        label=SwingLabel.FIRST,
        confirmed=True,
        confirmation_index=index + 2,
    )


@pytest.fixture
def long_frame():
    # Enough bars for indicator warmup
    return ohlcv([candle(100 + i * 0.01, 101 + i * 0.01, 99 + i * 0.01, 100 + i * 0.01) for i in range(80)])


def test_rsi_regular_bearish(monkeypatch, long_frame):
    n = len(long_frame)
    osc = pd.Series([50.0] * n)
    osc.iloc[40] = 70.0
    osc.iloc[60] = 60.0  # lower high in osc
    monkeypatch.setattr("patterns.divergence.rsi", lambda close, **kw: osc)
    monkeypatch.setattr(
        "patterns.divergence.macd_histogram",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    monkeypatch.setattr(
        "patterns.divergence.stoch_k",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    swings = [
        _sw(40, 110.0, SwingKind.HIGH),
        _sw(60, 120.0, SwingKind.HIGH),  # higher high in price
    ]
    hits = detect_divergences(long_frame, swings)
    assert any(h.name == PatternName.RSI_REGULAR_BEARISH for h in hits)
    hit = next(h for h in hits if h.name == PatternName.RSI_REGULAR_BEARISH)
    assert hit.direction == "bearish"
    assert hit.end_index == 62  # confirmation_index


def test_rsi_regular_bullish(monkeypatch, long_frame):
    n = len(long_frame)
    osc = pd.Series([50.0] * n)
    osc.iloc[40] = 30.0
    osc.iloc[60] = 40.0  # higher low in osc
    monkeypatch.setattr("patterns.divergence.rsi", lambda close, **kw: osc)
    monkeypatch.setattr(
        "patterns.divergence.macd_histogram",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    monkeypatch.setattr(
        "patterns.divergence.stoch_k",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    swings = [
        _sw(40, 90.0, SwingKind.LOW),
        _sw(60, 80.0, SwingKind.LOW),  # lower low in price
    ]
    hits = detect_divergences(long_frame, swings)
    assert any(h.name == PatternName.RSI_REGULAR_BULLISH for h in hits)


def test_rsi_hidden_bullish(monkeypatch, long_frame):
    n = len(long_frame)
    osc = pd.Series([50.0] * n)
    osc.iloc[40] = 40.0
    osc.iloc[60] = 30.0  # lower low osc
    monkeypatch.setattr("patterns.divergence.rsi", lambda close, **kw: osc)
    monkeypatch.setattr(
        "patterns.divergence.macd_histogram",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    monkeypatch.setattr(
        "patterns.divergence.stoch_k",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    swings = [
        _sw(40, 80.0, SwingKind.LOW),
        _sw(60, 90.0, SwingKind.LOW),  # higher low price
    ]
    hits = detect_divergences(long_frame, swings)
    assert any(h.name == PatternName.RSI_HIDDEN_BULLISH for h in hits)


def test_macd_and_stoch_names(monkeypatch, long_frame):
    n = len(long_frame)
    osc = pd.Series([0.0] * n)
    osc.iloc[40] = 1.0
    osc.iloc[60] = 0.5
    monkeypatch.setattr(
        "patterns.divergence.rsi",
        lambda close, **kw: pd.Series([float("nan")] * n),
    )
    monkeypatch.setattr("patterns.divergence.macd_histogram", lambda close, **kw: osc)
    monkeypatch.setattr("patterns.divergence.stoch_k", lambda close, **kw: osc)
    swings = [
        _sw(40, 110.0, SwingKind.HIGH),
        _sw(60, 120.0, SwingKind.HIGH),
    ]
    hits = detect_divergences(long_frame, swings)
    names = {h.name for h in hits}
    assert PatternName.MACD_REGULAR_BEARISH in names
    assert PatternName.STOCH_REGULAR_BEARISH in names


def test_insufficient_swings(long_frame):
    assert detect_divergences(long_frame, [_sw(10, 100.0, SwingKind.HIGH)]) == []
