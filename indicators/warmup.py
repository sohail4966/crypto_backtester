"""
Warmup bar estimates for indicator computation.

Used when loading OHLCV before the requested chart window so indicators are
seeded with real prior candles (TradingView-style), not cold-started on the
first visible bar.
"""

from __future__ import annotations

import math
from typing import Any

# Extra history multiplier so recursive indicators (Wilder RSI, EMA, etc.) stabilize
# across chart windows without loading full DB history.
WARMUP_MULTIPLIER = 10

# Bars of prior session needed for pivot points (D-35) by timeframe.
_PIVOT_WARMUP_BY_TIMEFRAME: dict[str, int] = {
    "1m": 1440,
    "5m": 288,
    "15m": 96,
    "1h": 24,
    "4h": 6,
    "1d": 1,
}


def _param_int(params: dict[str, Any], key: str, default: int) -> int:
    """Read a positive integer parameter with a default."""
    value = params.get(key, default)
    return int(value)


def _minimum_warmup_bars(key: str, params: dict[str, Any], *, timeframe: str = "1d") -> int:
    """Minimum bars an indicator needs before the window (before multiplier)."""
    indicator = key.upper()

    if indicator in {"OBV", "VOLUME", "NVI", "PVI", "AD"}:
        return 0

    if indicator in {"MACD_LINE", "MACD_SIGNAL", "MACD_HIST"}:
        slow = _param_int(params, "slow", 26)
        signal = _param_int(params, "signal", 9)
        return slow + signal

    if indicator in {"STOCH_K", "STOCH_D"}:
        return (
            _param_int(params, "fastk_period", 5)
            + _param_int(params, "slowk_period", 3)
            + _param_int(params, "slowd_period", 3)
        )

    if indicator in {"STOCHRSI_K", "STOCHRSI_D"}:
        return (
            _param_int(params, "period", 14)
            + _param_int(params, "fastk_period", 5)
            + _param_int(params, "fastd_period", 3)
        )

    if indicator == "ICHIMOKU_TENKAN":
        return _param_int(params, "tenkan", 9)
    if indicator == "ICHIMOKU_KIJUN":
        return _param_int(params, "kijun", 26)
    if indicator in {"ICHIMOKU_SENKOU_A", "ICHIMOKU_SENKOU_B"}:
        return _param_int(params, "senkou_b", 52) + _param_int(params, "displacement", 26)
    if indicator == "ICHIMOKU_CHIKOU":
        return _param_int(params, "displacement", 26)

    if indicator == "VOLRANK":
        return _param_int(params, "period", 100) + _param_int(params, "atr_period", 14)

    if indicator == "TSI":
        return _param_int(params, "long_period", 25) + _param_int(params, "short_period", 13)

    if indicator == "AO":
        return _param_int(params, "slow_period", 34)

    if indicator in {"VOLOSC", "VOLOSCILLATOR"}:
        return _param_int(params, "long_period", 10)

    if indicator == "HMA":
        period = _param_int(params, "period", 16)
        return period + max(int(math.sqrt(period)), 1)

    if indicator.startswith("PIVOT_"):
        return _PIVOT_WARMUP_BY_TIMEFRAME.get(timeframe, 24)

    if indicator == "SAR":
        return 5

    if indicator.startswith("BB_") or indicator == "BBP":
        return _param_int(params, "period", 20)

    if indicator.startswith("KELTNER_"):
        return _param_int(params, "period", 20)

    if indicator.startswith("DONCHIAN_"):
        return _param_int(params, "period", 20)

    if indicator == "ROC":
        return _param_int(params, "period", 10)

    if indicator == "STDDEV":
        return _param_int(params, "period", 5)

    if "period" in params:
        return _param_int(params, "period", 14)

    return 0


def warmup_bars(key: str, params: dict[str, Any], *, timeframe: str = "1d") -> int:
    """
    Estimate how many bars to load before the requested window for one indicator.

    The minimum lookback for the formula is scaled by ``WARMUP_MULTIPLIER`` (10×)
    so recursive smoothers converge across different chart windows.

    Args:
        key: Registry indicator key.
        params: Merged indicator parameters (defaults applied).
        timeframe: Candle resolution (needed for pivot session lookback).

    Returns:
        Extra bars to fetch before ``from``. Zero when no warmup is required.
    """
    minimum = _minimum_warmup_bars(key, params, timeframe=timeframe)
    if minimum == 0:
        return 0
    return minimum * WARMUP_MULTIPLIER


def frame_window_indices(
    unix_times: list[int],
    from_ts: int,
    to_ts: int,
) -> tuple[int, int]:
    """
    Locate inclusive bar indices for the visible output window.

    Args:
        unix_times: Bar open times (unix seconds) in ascending order.
        from_ts: Inclusive window start.
        to_ts: Inclusive window end.

    Returns:
        ``(start_idx, end_idx)`` inclusive indices into ``unix_times``.
        ``(-1, -1)`` when no bar falls in the window.
    """
    start_idx = -1
    end_idx = -1
    for idx, bar_time in enumerate(unix_times):
        if bar_time < from_ts:
            continue
        if bar_time > to_ts:
            break
        if start_idx < 0:
            start_idx = idx
        end_idx = idx
    return start_idx, end_idx
