"""
Classical chart pattern detection from confirmed swings (ROADMAP 5b).

Reference (D-99): Bulkowski Encyclopedia — pragmatic measurable rules for v1.
Confirmation = close beyond neckline / boundary (D-101 completed-only).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from patterns.types import PatternFamily, PatternHit, PatternName
from structure.ohlcv import candle_timestamps, require_ohlc
from structure.types import SwingKind, SwingPoint

CLASSICAL_EQ_TOLERANCE_PCT = 0.015
FLAG_IMPULSE_MIN_PCT = 0.03
BREAKOUT_LOOKAHEAD_BARS = 20
MIN_TRIANGLE_SWINGS = 5
HANDLE_MAX_RETRACE = 0.5


def _near(a: float, b: float, tol: float = CLASSICAL_EQ_TOLERANCE_PCT) -> bool:
    mid = (abs(a) + abs(b)) / 2.0 or 1.0
    return abs(a - b) / mid <= tol


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
        family=PatternFamily.CLASSICAL,
        direction=direction,  # type: ignore[arg-type]
        start_index=start,
        end_index=end,
        start_ts=stamps[start],
        end_ts=stamps[end],
        confidence=confidence,
        levels=levels,
    )


def _find_close_beyond(
    close: pd.Series,
    start_search: int,
    *,
    above: float | None = None,
    below: float | None = None,
    lookahead: int = BREAKOUT_LOOKAHEAD_BARS,
) -> int | None:
    n = len(close)
    end = min(n, start_search + lookahead + 1)
    for i in range(start_search, end):
        v = float(close.iloc[i])
        if above is not None and v > above:
            return i
        if below is not None and v < below:
            return i
    return None


def _highs(swings: Sequence[SwingPoint]) -> list[SwingPoint]:
    return [s for s in swings if s.kind == SwingKind.HIGH and s.confirmed]


def _lows(swings: Sequence[SwingPoint]) -> list[SwingPoint]:
    return [s for s in swings if s.kind == SwingKind.LOW and s.confirmed]


def _double_tops(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for i in range(len(highs) - 1):
        a, b = highs[i], highs[i + 1]
        if not _near(a.price, b.price):
            continue
        between = [low for low in lows if a.index < low.index < b.index]
        if not between:
            continue
        neck = min(between, key=lambda s: s.price)
        brk = _find_close_beyond(close, b.index + 1, below=neck.price)
        if brk is None:
            continue
        conf = 1.0 - abs(a.price - b.price) / ((a.price + b.price) / 2 or 1)
        hits.append(
            _hit(
                PatternName.DOUBLE_TOP,
                "bearish",
                a.index,
                brk,
                stamps,
                max(0.5, min(0.95, conf)),
                {"top1": a.price, "top2": b.price, "neckline": neck.price},
            )
        )
    return hits


def _double_bottoms(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for i in range(len(lows) - 1):
        a, b = lows[i], lows[i + 1]
        if not _near(a.price, b.price):
            continue
        between = [hi for hi in highs if a.index < hi.index < b.index]
        if not between:
            continue
        neck = max(between, key=lambda s: s.price)
        brk = _find_close_beyond(close, b.index + 1, above=neck.price)
        if brk is None:
            continue
        conf = 1.0 - abs(a.price - b.price) / ((a.price + b.price) / 2 or 1)
        hits.append(
            _hit(
                PatternName.DOUBLE_BOTTOM,
                "bullish",
                a.index,
                brk,
                stamps,
                max(0.5, min(0.95, conf)),
                {"bottom1": a.price, "bottom2": b.price, "neckline": neck.price},
            )
        )
    return hits


def _head_shoulders(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for i in range(len(highs) - 2):
        ls, head, rs = highs[i], highs[i + 1], highs[i + 2]
        if not (head.price > ls.price and head.price > rs.price):
            continue
        if not _near(ls.price, rs.price, tol=CLASSICAL_EQ_TOLERANCE_PCT * 1.5):
            continue
        left_low = [low for low in lows if ls.index < low.index < head.index]
        right_low = [low for low in lows if head.index < low.index < rs.index]
        if not left_low or not right_low:
            continue
        n1 = left_low[-1].price
        n2 = right_low[0].price
        neck = (n1 + n2) / 2.0
        brk = _find_close_beyond(close, rs.index + 1, below=neck)
        if brk is None:
            continue
        hits.append(
            _hit(
                PatternName.HEAD_AND_SHOULDERS,
                "bearish",
                ls.index,
                brk,
                stamps,
                0.8,
                {"left": ls.price, "head": head.price, "right": rs.price, "neckline": neck},
            )
        )
    return hits


def _inv_head_shoulders(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for i in range(len(lows) - 2):
        ls, head, rs = lows[i], lows[i + 1], lows[i + 2]
        if not (head.price < ls.price and head.price < rs.price):
            continue
        if not _near(ls.price, rs.price, tol=CLASSICAL_EQ_TOLERANCE_PCT * 1.5):
            continue
        left_hi = [hi for hi in highs if ls.index < hi.index < head.index]
        right_hi = [hi for hi in highs if head.index < hi.index < rs.index]
        if not left_hi or not right_hi:
            continue
        n1 = left_hi[-1].price
        n2 = right_hi[0].price
        neck = (n1 + n2) / 2.0
        brk = _find_close_beyond(close, rs.index + 1, above=neck)
        if brk is None:
            continue
        hits.append(
            _hit(
                PatternName.INV_HEAD_AND_SHOULDERS,
                "bullish",
                ls.index,
                brk,
                stamps,
                0.8,
                {"left": ls.price, "head": head.price, "right": rs.price, "neckline": neck},
            )
        )
    return hits


def _slope(points: list[SwingPoint]) -> float:
    if len(points) < 2:
        return 0.0
    x0, x1 = points[0].index, points[-1].index
    if x1 == x0:
        return 0.0
    return (points[-1].price - points[0].price) / (x1 - x0)


def _triangles(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if len(highs) < 2 or len(lows) < 2:
        return hits
    # Use last up to 3 highs and 3 lows that interleave in time
    hs = highs[-3:]
    ls = lows[-3:]
    if len(hs) < 2 or len(ls) < 2:
        return hits
    start = min(hs[0].index, ls[0].index)
    end_struct = max(hs[-1].index, ls[-1].index)
    if end_struct - start < MIN_TRIANGLE_SWINGS:
        return hits

    high_slope = _slope(hs)
    low_slope = _slope(ls)
    flat_tol = abs(hs[0].price) * 0.0005

    upper = hs[-1].price
    lower = ls[-1].price
    if upper <= lower:
        return hits

    # Ascending: flat highs, rising lows
    if abs(high_slope) <= flat_tol and low_slope > 0:
        brk = _find_close_beyond(close, end_struct + 1, above=upper)
        if brk is not None:
            hits.append(
                _hit(
                    PatternName.ASC_TRIANGLE,
                    "bullish",
                    start,
                    brk,
                    stamps,
                    0.75,
                    {"resistance": upper, "support": lower},
                )
            )
    # Descending: flat lows, falling highs
    elif abs(low_slope) <= flat_tol and high_slope < 0:
        brk = _find_close_beyond(close, end_struct + 1, below=lower)
        if brk is not None:
            hits.append(
                _hit(
                    PatternName.DESC_TRIANGLE,
                    "bearish",
                    start,
                    brk,
                    stamps,
                    0.75,
                    {"resistance": upper, "support": lower},
                )
            )
    # Symmetrical: falling highs + rising lows
    elif high_slope < 0 and low_slope > 0:
        brk_up = _find_close_beyond(close, end_struct + 1, above=upper)
        brk_dn = _find_close_beyond(close, end_struct + 1, below=lower)
        if brk_up is not None and (brk_dn is None or brk_up <= brk_dn):
            hits.append(
                _hit(
                    PatternName.SYM_TRIANGLE,
                    "bullish",
                    start,
                    brk_up,
                    stamps,
                    0.7,
                    {"resistance": upper, "support": lower},
                )
            )
        elif brk_dn is not None:
            hits.append(
                _hit(
                    PatternName.SYM_TRIANGLE,
                    "bearish",
                    start,
                    brk_dn,
                    stamps,
                    0.7,
                    {"resistance": upper, "support": lower},
                )
            )
    return hits


def _wedges(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if len(highs) < 2 or len(lows) < 2:
        return hits
    hs, ls = highs[-3:], lows[-3:]
    if len(hs) < 2 or len(ls) < 2:
        return hits
    hs_slope, ls_slope = _slope(hs), _slope(ls)
    start = min(hs[0].index, ls[0].index)
    end_struct = max(hs[-1].index, ls[-1].index)
    width0 = hs[0].price - ls[0].price
    width1 = hs[-1].price - ls[-1].price
    if width0 <= 0 or width1 >= width0:
        return hits  # must converge

    if hs_slope > 0 and ls_slope > 0:
        # rising wedge → bearish break
        brk = _find_close_beyond(close, end_struct + 1, below=ls[-1].price)
        if brk is not None:
            hits.append(
                _hit(
                    PatternName.RISING_WEDGE,
                    "bearish",
                    start,
                    brk,
                    stamps,
                    0.7,
                    {"upper": hs[-1].price, "lower": ls[-1].price},
                )
            )
    elif hs_slope < 0 and ls_slope < 0:
        brk = _find_close_beyond(close, end_struct + 1, above=hs[-1].price)
        if brk is not None:
            hits.append(
                _hit(
                    PatternName.FALLING_WEDGE,
                    "bullish",
                    start,
                    brk,
                    stamps,
                    0.7,
                    {"upper": hs[-1].price, "lower": ls[-1].price},
                )
            )
    return hits


def _flags_pennants(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    # Need impulse: prior swing move ≥ FLAG_IMPULSE_MIN_PCT, then short consolidation
    all_sw = sorted(highs + lows, key=lambda s: s.index)
    if len(all_sw) < 4:
        return hits

    for i in range(len(all_sw) - 3):
        a, b = all_sw[i], all_sw[i + 1]
        move = (b.price - a.price) / (abs(a.price) or 1.0)
        if abs(move) < FLAG_IMPULSE_MIN_PCT:
            continue
        consol = [s for s in all_sw if b.index < s.index <= all_sw[min(i + 5, len(all_sw) - 1)].index]
        if len(consol) < 2:
            continue
        consol_hs = [s for s in consol if s.kind == SwingKind.HIGH]
        consol_ls = [s for s in consol if s.kind == SwingKind.LOW]
        if len(consol_hs) < 1 or len(consol_ls) < 1:
            continue
        end_struct = consol[-1].index
        consol_range = max(s.price for s in consol) - min(s.price for s in consol)
        impulse_range = abs(b.price - a.price)
        if impulse_range <= 0 or consol_range / impulse_range > 0.6:
            continue

        converging = False
        if len(consol_hs) >= 2 and len(consol_ls) >= 2:
            w0 = consol_hs[0].price - consol_ls[0].price
            w1 = consol_hs[-1].price - consol_ls[-1].price
            converging = w1 < w0 * 0.85

        if move > 0:
            brk = _find_close_beyond(close, end_struct + 1, above=max(s.price for s in consol_hs))
            if brk is None:
                continue
            name = PatternName.PENNANT if converging else PatternName.BULL_FLAG
            hits.append(
                _hit(
                    name,
                    "bullish",
                    a.index,
                    brk,
                    stamps,
                    0.72,
                    {"impulse_start": a.price, "impulse_end": b.price},
                )
            )
        else:
            brk = _find_close_beyond(close, end_struct + 1, below=min(s.price for s in consol_ls))
            if brk is None:
                continue
            name = PatternName.PENNANT if converging else PatternName.BEAR_FLAG
            hits.append(
                _hit(
                    name,
                    "bearish",
                    a.index,
                    brk,
                    stamps,
                    0.72,
                    {"impulse_start": a.price, "impulse_end": b.price},
                )
            )
    return hits


def _cup_and_handle(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    close: pd.Series,
    stamps: pd.DatetimeIndex,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if len(lows) < 3 or len(highs) < 1:
        return hits
    for i in range(len(lows) - 2):
        left, cup, right = lows[i], lows[i + 1], lows[i + 2]
        if not (cup.price < left.price and cup.price < right.price):
            continue
        if not _near(left.price, right.price, tol=CLASSICAL_EQ_TOLERANCE_PCT * 2):
            continue
        depth = ((left.price + right.price) / 2 - cup.price) / ((left.price + right.price) / 2 or 1)
        if depth < 0.03 or depth > 0.5:
            continue
        # handle: shallow pullback after right rim — a low after a high after right
        post_highs = [h for h in highs if h.index > right.index]
        if not post_highs:
            continue
        handle_high = post_highs[0]
        post_lows = [low for low in lows if low.index > handle_high.index]
        if not post_lows:
            continue
        handle_low = post_lows[0]
        retrace = (handle_high.price - handle_low.price) / (handle_high.price - cup.price or 1)
        if retrace > HANDLE_MAX_RETRACE or handle_low.price < cup.price:
            continue
        brk = _find_close_beyond(close, handle_low.index + 1, above=right.price)
        if brk is None:
            continue
        hits.append(
            _hit(
                PatternName.CUP_AND_HANDLE,
                "bullish",
                left.index,
                brk,
                stamps,
                0.65,
                {"cup_low": cup.price, "rim": right.price, "handle_low": handle_low.price},
            )
        )
    return hits


def detect_classical_patterns(
    df: pd.DataFrame,
    swings: Sequence[SwingPoint],
) -> list[PatternHit]:
    """
    Detect ROADMAP 5b classical patterns using confirmed swing points.

    Args:
        df: OHLCV candles (needs ``close`` for breakout confirmation).
        swings: Swing points (provisional ignored).
    """
    frame = require_ohlc(df)
    if "close" not in frame.columns:
        raise ValueError("candles missing columns: ['close']")
    if frame.empty:
        return []

    close = frame["close"].astype(float).reset_index(drop=True)
    stamps = candle_timestamps(frame)
    confirmed = [s for s in swings if s.confirmed]
    highs = _highs(confirmed)
    lows = _lows(confirmed)

    hits: list[PatternHit] = []
    hits.extend(_double_tops(highs, lows, close, stamps))
    hits.extend(_double_bottoms(highs, lows, close, stamps))
    hits.extend(_head_shoulders(highs, lows, close, stamps))
    hits.extend(_inv_head_shoulders(highs, lows, close, stamps))
    hits.extend(_triangles(highs, lows, close, stamps))
    hits.extend(_wedges(highs, lows, close, stamps))
    hits.extend(_flags_pennants(highs, lows, close, stamps))
    hits.extend(_cup_and_handle(highs, lows, close, stamps))
    hits.sort(key=lambda h: (h.end_index, h.name.value))
    return hits
