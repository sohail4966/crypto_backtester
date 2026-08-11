"""
Tests for candlestick pattern detection (5a).
"""

from __future__ import annotations

from patterns.candles import detect_candlestick_patterns
from patterns.types import PatternName
from tests.patterns.helpers import candle, ohlcv


def test_bullish_engulfing():
    df = ohlcv(
        [
            candle(10, 10.5, 9.5, 9.6),  # bearish
            candle(9.5, 11.2, 9.4, 11.0),  # bullish engulfing body
        ]
    )
    hits = detect_candlestick_patterns(df)
    names = {h.name for h in hits}
    assert PatternName.BULLISH_ENGULFING in names
    hit = next(h for h in hits if h.name == PatternName.BULLISH_ENGULFING)
    assert hit.direction == "bullish"
    assert hit.end_index == 1


def test_bearish_engulfing():
    df = ohlcv(
        [
            candle(9.5, 10.5, 9.4, 10.4),
            candle(10.5, 10.6, 9.0, 9.1),
        ]
    )
    hits = detect_candlestick_patterns(df)
    assert any(h.name == PatternName.BEARISH_ENGULFING for h in hits)


def test_hammer():
    df = ohlcv([candle(10.0, 10.2, 8.0, 10.1)])
    hits = detect_candlestick_patterns(df)
    assert any(h.name == PatternName.HAMMER and h.direction == "bullish" for h in hits)


def test_shooting_star_or_inverted_hammer():
    df = ohlcv([candle(10.0, 12.0, 9.9, 10.1)])
    hits = detect_candlestick_patterns(df)
    names = {h.name for h in hits}
    assert PatternName.SHOOTING_STAR in names or PatternName.INVERTED_HAMMER in names


def test_doji_variants():
    standard = ohlcv([candle(10.0, 10.5, 9.5, 10.01)])
    gravestone = ohlcv([candle(10.0, 11.5, 9.95, 10.02)])
    dragonfly = ohlcv([candle(10.0, 10.05, 8.5, 10.01)])
    assert any(h.name == PatternName.DOJI for h in detect_candlestick_patterns(standard))
    assert any(h.name == PatternName.GRAVESTONE_DOJI for h in detect_candlestick_patterns(gravestone))
    assert any(h.name == PatternName.DRAGONFLY_DOJI for h in detect_candlestick_patterns(dragonfly))


def test_morning_evening_star():
    morning = ohlcv(
        [
            candle(11.0, 11.2, 10.0, 10.1),  # bearish
            candle(10.05, 10.2, 9.9, 10.0),  # small
            candle(10.1, 11.5, 10.0, 11.3),  # bullish close above mid
        ]
    )
    evening = ohlcv(
        [
            candle(10.0, 11.2, 9.9, 11.1),
            candle(11.05, 11.2, 10.9, 11.0),
            candle(10.9, 11.0, 9.5, 9.6),
        ]
    )
    assert any(h.name == PatternName.MORNING_STAR for h in detect_candlestick_patterns(morning))
    assert any(h.name == PatternName.EVENING_STAR for h in detect_candlestick_patterns(evening))


def test_three_soldiers_and_crows():
    soldiers = ohlcv(
        [
            candle(10.0, 10.8, 9.9, 10.7),
            candle(10.7, 11.5, 10.6, 11.4),
            candle(11.4, 12.2, 11.3, 12.1),
        ]
    )
    crows = ohlcv(
        [
            candle(12.0, 12.1, 11.2, 11.3),
            candle(11.3, 11.4, 10.4, 10.5),
            candle(10.5, 10.6, 9.6, 9.7),
        ]
    )
    assert any(h.name == PatternName.THREE_WHITE_SOLDIERS for h in detect_candlestick_patterns(soldiers))
    assert any(h.name == PatternName.THREE_BLACK_CROWS for h in detect_candlestick_patterns(crows))


def test_harami():
    bullish = ohlcv(
        [
            candle(11.0, 11.2, 9.5, 9.6),
            candle(10.0, 10.4, 9.8, 10.3),
        ]
    )
    bearish = ohlcv(
        [
            candle(9.5, 11.2, 9.4, 11.1),
            candle(10.5, 10.8, 10.2, 10.3),
        ]
    )
    assert any(h.name == PatternName.BULLISH_HARAMI for h in detect_candlestick_patterns(bullish))
    assert any(h.name == PatternName.BEARISH_HARAMI for h in detect_candlestick_patterns(bearish))


def test_empty_frame():
    df = ohlcv([])
    assert detect_candlestick_patterns(df) == []
