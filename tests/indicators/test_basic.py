"""
Tests for indicators.basic — including RSI regression on stored BTC/USDT 1d closes.
"""

from pathlib import Path

import pandas as pd
import pytest

from indicators.basic import rsi, sma

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "btc_usdt_1d_closes.csv"

# Wilder RSI(14) on the fixture closes (Binance BTC/USDT 1d via ccxt).
# Cross-check against TradingView when updating the fixture (POC HLD step 3).
RSI_REGRESSION_CASES: list[tuple[str, float]] = [
    ("2024-08-05", 26.4012),
    ("2024-11-22", 82.1575),
    ("2025-02-26", 24.1335),
]


def _load_fixture_closes() -> pd.Series:
    """Load close prices from the committed BTC/USDT daily fixture."""
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["ts"])
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    return frame.set_index("ts")["close"]


def test_sma_period_invalid_raises_value_error() -> None:
    """SMA must reject non-positive period."""
    close_series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="period must be >= 1"):
        sma(close_series, period=0)


def test_sma_series_shorter_than_period_raises_value_error() -> None:
    """SMA must reject windows longer than the input series."""
    close_series = pd.Series([1.0, 2.0])
    with pytest.raises(ValueError, match="shorter than period"):
        sma(close_series, period=3)


def test_sma_period_3_returns_expected_mean() -> None:
    """SMA(3) on a short series matches hand-calculated rolling mean."""
    close_series = pd.Series([10.0, 20.0, 30.0, 40.0])
    result = sma(close_series, period=3)
    assert result.iloc[2] == pytest.approx(20.0)
    assert result.iloc[3] == pytest.approx(30.0)


def test_rsi_period_too_small_raises_value_error() -> None:
    """RSI period must be at least 2."""
    close_series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="period must be >= 2"):
        rsi(close_series, period=1)


def test_rsi_matches_regression_fixture_on_btc_daily() -> None:
    """
    RSI(14) matches regression baselines on committed BTC/USDT 1d close data.

    Baselines were produced by Wilder's RMA on Binance-sourced candles. Re-verify
    against TradingView when the fixture is refreshed.
    """
    close_series = _load_fixture_closes()
    rsi_series = rsi(close_series, period=14)
    for date_str, expected_rsi in RSI_REGRESSION_CASES:
        timestamp = pd.Timestamp(date_str, tz="UTC")
        actual = float(rsi_series.loc[timestamp])
        assert actual == pytest.approx(
            expected_rsi, abs=0.0001
        ), f"RSI on {date_str}: expected {expected_rsi}, got {actual}"


def test_rsi_all_gains_returns_100() -> None:
    """Monotonically rising prices produce RSI of 100 once seeded."""
    close_series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    rsi_series = rsi(close_series, period=2)
    assert rsi_series.iloc[-1] == pytest.approx(100.0)
