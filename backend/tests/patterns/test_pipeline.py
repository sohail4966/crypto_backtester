"""
Tests for analyze_patterns pipeline and Series packing.
"""

from __future__ import annotations

from patterns.pipeline import analyze_patterns
from patterns.series import hits_to_signals
from patterns.types import PatternFamily, PatternHit, PatternName
from structure.ohlcv import candle_timestamps
from tests.patterns.helpers import candle, ohlcv


def test_analyze_patterns_candle_only():
    df = ohlcv(
        [
            candle(10, 10.5, 9.5, 9.6),
            candle(9.5, 11.2, 9.4, 11.0),
        ]
    )
    result = analyze_patterns(df, families=[PatternFamily.CANDLE])
    assert any(h.name == PatternName.BULLISH_ENGULFING for h in result.hits)
    series = result.signals["bullish_engulfing"]
    assert bool(series.iloc[1]) is True
    assert bool(series.iloc[0]) is False


def test_hits_to_signals_sparse():
    df = ohlcv([candle(10, 11, 9, 10)] * 5)
    index = candle_timestamps(df)
    hit = PatternHit(
        name=PatternName.DOJI,
        family=PatternFamily.CANDLE,
        direction="bullish",
        start_index=2,
        end_index=2,
        start_ts=index[2],
        end_ts=index[2],
        confidence=0.5,
        levels={},
    )
    signals = hits_to_signals([hit], index)
    assert list(signals["doji"].astype(int)) == [0, 0, 1, 0, 0]


def test_empty_analyze():
    result = analyze_patterns(ohlcv([]))
    assert result.hits == []
    assert result.signals == {}


def test_multiple_patterns_same_bar_independent():
    df = ohlcv([candle(10.0, 10.5, 9.5, 10.01)])  # doji-ish
    result = analyze_patterns(df, families=[PatternFamily.CANDLE])
    # May emit doji; Series keys independent
    for series in result.signals.values():
        assert series.dtype == bool
