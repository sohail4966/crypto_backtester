"""
Helpers: OHLCV normalize + confirmed swings usable at a bar (no lookahead).
"""

from __future__ import annotations

import pandas as pd

from structure.ohlcv import candle_timestamps, require_ohlc
from structure.pipeline import analyze_structure
from structure.types import StructureResult, SwingKind, SwingPoint, Trend


def prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Validate OHLC and ensure open/close/high/low exist as float columns."""
    frame = require_ohlc(df)
    required = {"open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"candles missing columns: {sorted(missing)}")
    out = frame.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = out[col].astype(float)
    return out


def structure_for(df: pd.DataFrame, *, left_bars: int, right_bars: int) -> StructureResult:
    """Run Phase 5 structure with confirmed swings only (backtest-safe)."""
    return analyze_structure(
        df,
        left_bars=left_bars,
        right_bars=right_bars,
        confirmed_only=True,
    )


def usable_swings(swings: list[SwingPoint], bar_index: int) -> list[SwingPoint]:
    """Confirmed swings known by ``bar_index`` (confirmation_index <= bar)."""
    return [
        s
        for s in swings
        if s.confirmed
        and s.confirmation_index is not None
        and s.confirmation_index <= bar_index
    ]


def last_swing(swings: list[SwingPoint], kind: SwingKind) -> SwingPoint | None:
    """Most recent usable swing of the given kind."""
    matched = [s for s in swings if s.kind is kind]
    return matched[-1] if matched else None


def trend_at(trend: pd.Series, bar_index: int) -> Trend:
    """Trend enum at positional bar index."""
    if bar_index < 0 or bar_index >= len(trend):
        return Trend.UNDEFINED
    value = trend.iloc[bar_index]
    if isinstance(value, Trend):
        return value
    return Trend(str(value))


def event_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """UTC DatetimeIndex aligned to candle rows."""
    return pd.DatetimeIndex(candle_timestamps(df))
