"""
Candlestick pattern detection (ROADMAP 5a).

Reference (D-99): Steve Nison / industry-standard body–wick geometry.
"""

from __future__ import annotations

import pandas as pd

from patterns.types import PatternFamily, PatternHit, PatternName
from structure.ohlcv import candle_timestamps, require_ohlc

DOJI_BODY_MAX_RATIO = 0.1
HAMMER_LOWER_WICK_MIN = 2.0
HAMMER_UPPER_WICK_MAX_RATIO = 0.3  # upper wick / range
SHOOTING_UPPER_WICK_MIN = 2.0
SHOOTING_LOWER_WICK_MAX_RATIO = 0.3  # lower wick / range
STAR_GAP_BODY_RATIO = 0.3
SOLDIER_BODY_MIN_RATIO = 0.5


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _range(h: float, low: float) -> float:
    return max(h - low, 1e-12)


def _upper_wick(o: float, h: float, c: float) -> float:
    return h - max(o, c)


def _lower_wick(o: float, low: float, c: float) -> float:
    return min(o, c) - low


def _is_bull(o: float, c: float) -> bool:
    return c > o


def _is_bear(o: float, c: float) -> bool:
    return c < o


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
        family=PatternFamily.CANDLE,
        direction=direction,  # type: ignore[arg-type]
        start_index=start,
        end_index=end,
        start_ts=stamps[start],
        end_ts=stamps[end],
        confidence=confidence,
        levels=levels,
    )


def detect_candlestick_patterns(df: pd.DataFrame) -> list[PatternHit]:
    """
    Detect ROADMAP 5a candlestick patterns on an OHLCV frame.

    Emits hits only when the pattern is complete (last bar of the formation).
    """
    frame = require_ohlc(df)
    for col in ("open", "close"):
        if col not in frame.columns:
            raise ValueError(f"candles missing columns: ['{col}']")
    if frame.empty:
        return []

    o = frame["open"].astype(float).reset_index(drop=True)
    h = frame["high"].astype(float).reset_index(drop=True)
    low = frame["low"].astype(float).reset_index(drop=True)
    c = frame["close"].astype(float).reset_index(drop=True)
    stamps = candle_timestamps(frame)
    n = len(frame)
    hits: list[PatternHit] = []

    for i in range(n):
        oi, hi, li, ci = float(o.iloc[i]), float(h.iloc[i]), float(low.iloc[i]), float(c.iloc[i])
        rng = _range(hi, li)
        body = _body(oi, ci)
        uw = _upper_wick(oi, hi, ci)
        lw = _lower_wick(oi, li, ci)
        body_ratio = body / rng

        # --- single-bar: doji family ---
        if body_ratio <= DOJI_BODY_MAX_RATIO:
            if uw >= 2 * max(lw, 1e-12) and uw / rng >= 0.6:
                hits.append(
                    _hit(
                        PatternName.GRAVESTONE_DOJI,
                        "bearish",
                        i,
                        i,
                        stamps,
                        0.7,
                        {"high": hi, "low": li},
                    )
                )
            elif lw >= 2 * max(uw, 1e-12) and lw / rng >= 0.6:
                hits.append(
                    _hit(
                        PatternName.DRAGONFLY_DOJI,
                        "bullish",
                        i,
                        i,
                        stamps,
                        0.7,
                        {"high": hi, "low": li},
                    )
                )
            else:
                hits.append(
                    _hit(PatternName.DOJI, "bearish" if _is_bear(oi, ci) else "bullish", i, i, stamps, 0.55, {"high": hi, "low": li})
                )

        # --- single-bar: hammer / inverted / shooting star ---
        if body > 0:
            if lw >= HAMMER_LOWER_WICK_MIN * body and uw / rng <= HAMMER_UPPER_WICK_MAX_RATIO:
                if (ci - li) / rng >= 0.6:
                    hits.append(
                        _hit(PatternName.HAMMER, "bullish", i, i, stamps, 0.75, {"low": li, "high": hi})
                    )
            if uw >= SHOOTING_UPPER_WICK_MIN * body and lw / rng <= SHOOTING_LOWER_WICK_MAX_RATIO:
                if (hi - ci) / rng >= 0.6:
                    hits.append(
                        _hit(
                            PatternName.INVERTED_HAMMER,
                            "bullish",
                            i,
                            i,
                            stamps,
                            0.65,
                            {"high": hi, "low": li},
                        )
                    )
                    hits.append(
                        _hit(
                            PatternName.SHOOTING_STAR,
                            "bearish",
                            i,
                            i,
                            stamps,
                            0.7,
                            {"high": hi, "low": li},
                        )
                    )

        if i < 1:
            continue

        # --- two-bar: engulfing / harami ---
        op, hp, lp, cp = float(o.iloc[i - 1]), float(h.iloc[i - 1]), float(low.iloc[i - 1]), float(c.iloc[i - 1])
        prev_body_top = max(op, cp)
        prev_body_bot = min(op, cp)
        cur_body_top = max(oi, ci)
        cur_body_bot = min(oi, ci)

        if _is_bear(op, cp) and _is_bull(oi, ci) and cur_body_bot <= prev_body_bot and cur_body_top >= prev_body_top:
            hits.append(
                _hit(
                    PatternName.BULLISH_ENGULFING,
                    "bullish",
                    i - 1,
                    i,
                    stamps,
                    0.85,
                    {"prior_close": cp, "close": ci},
                )
            )
        if _is_bull(op, cp) and _is_bear(oi, ci) and cur_body_bot <= prev_body_bot and cur_body_top >= prev_body_top:
            hits.append(
                _hit(
                    PatternName.BEARISH_ENGULFING,
                    "bearish",
                    i - 1,
                    i,
                    stamps,
                    0.85,
                    {"prior_close": cp, "close": ci},
                )
            )

        if _is_bear(op, cp) and _is_bull(oi, ci) and cur_body_bot >= prev_body_bot and cur_body_top <= prev_body_top:
            if body < _body(op, cp):
                hits.append(
                    _hit(
                        PatternName.BULLISH_HARAMI,
                        "bullish",
                        i - 1,
                        i,
                        stamps,
                        0.7,
                        {"prior_close": cp, "close": ci},
                    )
                )
        if _is_bull(op, cp) and _is_bear(oi, ci) and cur_body_bot >= prev_body_bot and cur_body_top <= prev_body_top:
            if body < _body(op, cp):
                hits.append(
                    _hit(
                        PatternName.BEARISH_HARAMI,
                        "bearish",
                        i - 1,
                        i,
                        stamps,
                        0.7,
                        {"prior_close": cp, "close": ci},
                    )
                )

        if i < 2:
            continue

        # --- three-bar: morning / evening star, soldiers / crows ---
        o0, c0 = float(o.iloc[i - 2]), float(c.iloc[i - 2])
        o1, h1, l1, c1 = float(o.iloc[i - 1]), float(h.iloc[i - 1]), float(low.iloc[i - 1]), float(c.iloc[i - 1])
        mid_body = _body(o1, c1)
        mid_rng = _range(h1, l1)

        if (
            _is_bear(o0, c0)
            and mid_body / mid_rng <= STAR_GAP_BODY_RATIO
            and _is_bull(oi, ci)
            and ci > (o0 + c0) / 2
        ):
            hits.append(
                _hit(
                    PatternName.MORNING_STAR,
                    "bullish",
                    i - 2,
                    i,
                    stamps,
                    0.8,
                    {"mid_low": l1, "close": ci},
                )
            )
        if (
            _is_bull(o0, c0)
            and mid_body / mid_rng <= STAR_GAP_BODY_RATIO
            and _is_bear(oi, ci)
            and ci < (o0 + c0) / 2
        ):
            hits.append(
                _hit(
                    PatternName.EVENING_STAR,
                    "bearish",
                    i - 2,
                    i,
                    stamps,
                    0.8,
                    {"mid_high": h1, "close": ci},
                )
            )

        bodies = [_body(float(o.iloc[i - 2 + k]), float(c.iloc[i - 2 + k])) for k in range(3)]
        ranges = [_range(float(h.iloc[i - 2 + k]), float(low.iloc[i - 2 + k])) for k in range(3)]
        bullish3 = all(
            _is_bull(float(o.iloc[i - 2 + k]), float(c.iloc[i - 2 + k]))
            and bodies[k] / ranges[k] >= SOLDIER_BODY_MIN_RATIO
            for k in range(3)
        )
        bearish3 = all(
            _is_bear(float(o.iloc[i - 2 + k]), float(c.iloc[i - 2 + k]))
            and bodies[k] / ranges[k] >= SOLDIER_BODY_MIN_RATIO
            for k in range(3)
        )
        rising = float(c.iloc[i - 2]) < float(c.iloc[i - 1]) < float(c.iloc[i])
        falling = float(c.iloc[i - 2]) > float(c.iloc[i - 1]) > float(c.iloc[i])
        if bullish3 and rising:
            hits.append(
                _hit(
                    PatternName.THREE_WHITE_SOLDIERS,
                    "bullish",
                    i - 2,
                    i,
                    stamps,
                    0.8,
                    {"close": ci},
                )
            )
        if bearish3 and falling:
            hits.append(
                _hit(
                    PatternName.THREE_BLACK_CROWS,
                    "bearish",
                    i - 2,
                    i,
                    stamps,
                    0.8,
                    {"close": ci},
                )
            )

    return hits
