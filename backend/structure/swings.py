"""
Symmetric pivot swing high / low detection (D-53, D-62).
"""

from __future__ import annotations

import pandas as pd

from structure.ohlcv import candle_timestamps, require_ohlc
from structure.types import SwingKind, SwingLabel, SwingPoint

DEFAULT_LEFT_BARS = 5
DEFAULT_RIGHT_BARS = 5


def _is_pivot_high(high: pd.Series, i: int, left: int, right_end: int) -> bool:
    """Return True if bar i is a strict swing high versus left and available right."""
    pivot = float(high.iloc[i])
    left_window = high.iloc[i - left : i]
    if (left_window >= pivot).any():
        return False
    right_window = high.iloc[i + 1 : right_end]
    if len(right_window) == 0:
        return True
    return not bool((right_window >= pivot).any())


def _is_pivot_low(low: pd.Series, i: int, left: int, right_end: int) -> bool:
    """Return True if bar i is a strict swing low versus left and available right."""
    pivot = float(low.iloc[i])
    left_window = low.iloc[i - left : i]
    if (left_window <= pivot).any():
        return False
    right_window = low.iloc[i + 1 : right_end]
    if len(right_window) == 0:
        return True
    return not bool((right_window <= pivot).any())


def detect_swings(
    df: pd.DataFrame,
    *,
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
    confirmed_only: bool = False,
) -> list[SwingPoint]:
    """
    Detect swing highs and lows with the symmetric pivot method.

    A swing at bar ``i`` requires ``left_bars`` completed left neighbors. It is
    **confirmed** when ``right_bars`` right neighbors exist; otherwise it may be
    emitted as provisional when it is extreme versus all available right bars.

    Args:
        df: OHLCV candles with ``high`` / ``low`` and ``ts`` or a DatetimeIndex.
        left_bars: Bars to the left of the pivot. Default 5.
        right_bars: Bars to the right required for confirmation. Default 5.
        confirmed_only: When True, drop provisional swings (backtest-safe default
            for consumers that filter after detection).

    Returns:
        Swing points in ascending bar order. Labels are ``FIRST`` placeholders;
        call ``label_swings`` to assign structural labels.

    Raises:
        ValueError: If OHLC columns are missing or bar counts are invalid.
    """
    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be >= 1")

    frame = require_ohlc(df)
    if frame.empty:
        return []

    high = frame["high"].astype(float).reset_index(drop=True)
    low = frame["low"].astype(float).reset_index(drop=True)
    stamps = candle_timestamps(frame)
    n = len(frame)
    swings: list[SwingPoint] = []

    for i in range(left_bars, n):
        can_confirm = i + right_bars < n
        if can_confirm:
            right_end = i + right_bars + 1
            if _is_pivot_high(high, i, left_bars, right_end):
                swings.append(
                    SwingPoint(
                        index=i,
                        ts=stamps[i],
                        price=float(high.iloc[i]),
                        kind=SwingKind.HIGH,
                        label=SwingLabel.FIRST,
                        confirmed=True,
                        confirmation_index=i + right_bars,
                    )
                )
            if _is_pivot_low(low, i, left_bars, right_end):
                swings.append(
                    SwingPoint(
                        index=i,
                        ts=stamps[i],
                        price=float(low.iloc[i]),
                        kind=SwingKind.LOW,
                        label=SwingLabel.FIRST,
                        confirmed=True,
                        confirmation_index=i + right_bars,
                    )
                )
            continue

        # Trailing window: provisional candidates only.
        right_end = n
        if _is_pivot_high(high, i, left_bars, right_end):
            swings.append(
                SwingPoint(
                    index=i,
                    ts=stamps[i],
                    price=float(high.iloc[i]),
                    kind=SwingKind.HIGH,
                    label=SwingLabel.FIRST,
                    confirmed=False,
                    confirmation_index=None,
                )
            )
        if _is_pivot_low(low, i, left_bars, right_end):
            swings.append(
                SwingPoint(
                    index=i,
                    ts=stamps[i],
                    price=float(low.iloc[i]),
                    kind=SwingKind.LOW,
                    label=SwingLabel.FIRST,
                    confirmed=False,
                    confirmation_index=None,
                )
            )

    if confirmed_only:
        return [s for s in swings if s.confirmed]
    return swings
