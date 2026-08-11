"""
Indicator divergence detection (ROADMAP 5c).

Reference (D-99): Murphy / standard TA — price pivots vs oscillator samples.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from indicators.talib_wrappers import macd_histogram, rsi, stoch_k
from patterns.types import PatternFamily, PatternHit, PatternName
from structure.ohlcv import candle_timestamps, require_ohlc
from structure.types import SwingKind, SwingPoint

OSC_EQ_TOL = 1e-9


def _hit(
    name: PatternName,
    direction: str,
    start: int,
    end: int,
    stamps: pd.DatetimeIndex,
    confidence: float,
    levels: dict[str, float],
) -> PatternHit:
    return PatternHit(
        name=name,
        family=PatternFamily.DIVERGENCE,
        direction=direction,  # type: ignore[arg-type]
        start_index=start,
        end_index=end,
        start_ts=stamps[start],
        end_ts=stamps[end],
        confidence=confidence,
        levels=levels,
    )


def _sample(series: pd.Series, idx: int) -> float | None:
    if idx < 0 or idx >= len(series):
        return None
    val = series.iloc[idx]
    if pd.isna(val):
        return None
    return float(val)


def _div_from_pair(
    *,
    p1: float,
    p2: float,
    o1: float,
    o2: float,
    kind: str,
) -> tuple[str, PatternName] | None:
    """
    Return (direction_kind, pattern suffix role) for regular/hidden.

    kind is 'high' for bearish-side pivots or 'low' for bullish-side.
    """
    price_up = p2 > p1 + OSC_EQ_TOL
    price_dn = p2 < p1 - OSC_EQ_TOL
    osc_up = o2 > o1 + OSC_EQ_TOL
    osc_dn = o2 < o1 - OSC_EQ_TOL
    if not (price_up or price_dn) or not (osc_up or osc_dn):
        return None

    if kind == "high":
        if price_up and osc_dn:
            return ("regular", "bearish")
        if price_dn and osc_up:
            return ("hidden", "bearish")
    else:
        if price_dn and osc_up:
            return ("regular", "bullish")
        if price_up and osc_dn:
            return ("hidden", "bullish")
    return None


_NAME_MAP: dict[tuple[str, str, str], PatternName] = {
    ("rsi", "regular", "bullish"): PatternName.RSI_REGULAR_BULLISH,
    ("rsi", "regular", "bearish"): PatternName.RSI_REGULAR_BEARISH,
    ("rsi", "hidden", "bullish"): PatternName.RSI_HIDDEN_BULLISH,
    ("rsi", "hidden", "bearish"): PatternName.RSI_HIDDEN_BEARISH,
    ("macd", "regular", "bullish"): PatternName.MACD_REGULAR_BULLISH,
    ("macd", "regular", "bearish"): PatternName.MACD_REGULAR_BEARISH,
    ("macd", "hidden", "bullish"): PatternName.MACD_HIDDEN_BULLISH,
    ("macd", "hidden", "bearish"): PatternName.MACD_HIDDEN_BEARISH,
    ("stoch", "regular", "bullish"): PatternName.STOCH_REGULAR_BULLISH,
    ("stoch", "regular", "bearish"): PatternName.STOCH_REGULAR_BEARISH,
    ("stoch", "hidden", "bullish"): PatternName.STOCH_HIDDEN_BULLISH,
    ("stoch", "hidden", "bearish"): PatternName.STOCH_HIDDEN_BEARISH,
}


def _scan_oscillator(
    prefix: str,
    osc: pd.Series,
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for pivots, side in ((highs, "high"), (lows, "low")):
        for i in range(len(pivots) - 1):
            a, b = pivots[i], pivots[i + 1]
            o1 = _sample(osc, a.index)
            o2 = _sample(osc, b.index)
            if o1 is None or o2 is None:
                continue
            parsed = _div_from_pair(p1=a.price, p2=b.price, o1=o1, o2=o2, kind=side)
            if parsed is None:
                continue
            mode, direction = parsed
            name = _NAME_MAP[(prefix, mode, direction)]
            end = b.confirmation_index if b.confirmation_index is not None else b.index
            end = min(end, len(stamps) - 1)
            conf = min(0.95, 0.55 + abs(o1 - o2) / (abs(o1) + abs(o2) + 1e-9))
            hits.append(
                _hit(
                    name,
                    direction,
                    a.index,
                    end,
                    stamps,
                    conf,
                    {
                        "price1": a.price,
                        "price2": b.price,
                        "osc1": o1,
                        "osc2": o2,
                    },
                )
            )
    return hits


def detect_divergences(
    df: pd.DataFrame,
    swings: Sequence[SwingPoint],
    *,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
) -> list[PatternHit]:
    """
    Detect RSI / MACD histogram / Stochastic regular and hidden divergences.

    Oscillator values are sampled at confirmed price swing indices (Q10).
    """
    frame = require_ohlc(df)
    if "close" not in frame.columns:
        raise ValueError("candles missing columns: ['close']")
    if frame.empty:
        return []

    close = frame["close"].astype(float)
    # Align indicator Series to positional index for sampling by swing.index
    close_pos = close.reset_index(drop=True)
    high_s = (high if high is not None else frame["high"].astype(float)).reset_index(drop=True)
    low_s = (low if low is not None else frame["low"].astype(float)).reset_index(drop=True)
    stamps = candle_timestamps(frame)

    confirmed = [s for s in swings if s.confirmed]
    highs = [s for s in confirmed if s.kind == SwingKind.HIGH]
    lows = [s for s in confirmed if s.kind == SwingKind.LOW]
    if len(highs) < 2 and len(lows) < 2:
        return []

    hits: list[PatternHit] = []
    try:
        rsi_s = rsi(close_pos).reset_index(drop=True)
        hits.extend(_scan_oscillator("rsi", rsi_s, highs, lows, stamps))
    except ValueError:
        pass

    try:
        macd_s = macd_histogram(close_pos).reset_index(drop=True)
        hits.extend(_scan_oscillator("macd", macd_s, highs, lows, stamps))
    except ValueError:
        pass

    try:
        stoch_s = stoch_k(close_pos, high=high_s, low=low_s).reset_index(drop=True)
        hits.extend(_scan_oscillator("stoch", stoch_s, highs, lows, stamps))
    except ValueError:
        pass

    hits.sort(key=lambda h: (h.end_index, h.name.value))
    return hits
