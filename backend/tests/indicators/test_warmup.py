"""Tests for indicator warmup bar estimation."""

from __future__ import annotations

from indicators.warmup import WARMUP_MULTIPLIER, frame_window_indices, warmup_bars


def test_warmup_bars_rsi_uses_ten_times_period() -> None:
    """RSI warmup is 10× the requested period."""
    assert warmup_bars("RSI", {"period": 14}) == 14 * WARMUP_MULTIPLIER
    assert warmup_bars("RSI", {"period": 28}) == 28 * WARMUP_MULTIPLIER


def test_warmup_bars_macd_uses_ten_times_slow_plus_signal() -> None:
    """MACD warmup is 10× (slow + signal)."""
    base = 26 + 9
    assert warmup_bars("MACD_LINE", {"fast": 12, "slow": 26, "signal": 9}) == base * WARMUP_MULTIPLIER


def test_warmup_bars_obv_is_zero() -> None:
    """Cumulative volume indicators need no lookback bars."""
    assert warmup_bars("OBV", {}) == 0


def test_frame_window_indices_selects_visible_range() -> None:
    """Window indices include only bars between from and to."""
    times = [100, 200, 300, 400, 500]
    assert frame_window_indices(times, 200, 400) == (1, 3)
