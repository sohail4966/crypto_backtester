"""
Tests for TA-Lib indicator wrappers (Tier 1).
"""

import pandas as pd
import pytest

from indicators.registry import INDICATOR_META, INDICATORS
from indicators.talib_wrappers import (
    adx,
    atr,
    bb_lower,
    bb_middle,
    bb_upper,
    ema,
    macd_histogram,
    macd_line,
    macd_signal,
    obv,
    rsi,
    sma,
    stoch_d,
    stoch_k,
    volume_passthrough,
    wma,
)


def _ohlcv(length: int = 30) -> dict[str, pd.Series]:
    """Synthetic OHLCV series long enough for Tier 1 warmup."""
    index = pd.date_range("2024-01-01", periods=length, freq="D", tz="UTC")
    close = pd.Series([100.0 + i for i in range(length)], index=index)
    return {
        "close": close,
        "high": close + 2.0,
        "low": close - 2.0,
        "volume": pd.Series([1000.0 + i * 10 for i in range(length)], index=index),
    }


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


def test_rsi_series_shorter_than_period_raises_value_error() -> None:
    """RSI must reject windows longer than the input series."""
    close_series = pd.Series([1.0, 2.0])
    with pytest.raises(ValueError, match="shorter than period"):
        rsi(close_series, period=14)


def test_rsi_all_gains_returns_100() -> None:
    """Monotonically rising prices produce RSI of 100 once seeded."""
    close_series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    rsi_series = rsi(close_series, period=2)
    assert rsi_series.iloc[-1] == pytest.approx(100.0)


def test_rsi_output_index_aligns_with_close() -> None:
    """RSI output shares the same index as the input close series."""
    index = pd.date_range("2024-01-01", periods=20, freq="D", tz="UTC")
    close_series = pd.Series(range(20), index=index, dtype=float)
    rsi_series = rsi(close_series, period=14)
    assert rsi_series.index.equals(close_series.index)
    assert rsi_series.iloc[:14].isna().all()
    assert (rsi_series.iloc[14:] >= 0).all()
    assert (rsi_series.iloc[14:] <= 100).all()


@pytest.mark.parametrize(
    ("name", "fn", "kwargs"),
    [
        ("EMA", ema, {"period": 5}),
        ("WMA", wma, {"period": 5}),
    ],
)
def test_close_only_indicators_return_aligned_series(
    name: str,
    fn: object,
    kwargs: dict[str, int],
) -> None:
    """Close-only moving averages return float Series aligned to input."""
    data = _ohlcv()
    result = fn(data["close"], **kwargs)  # type: ignore[operator]
    assert isinstance(result, pd.Series)
    assert result.index.equals(data["close"].index)
    assert result.dtype == float
    period = kwargs["period"]
    assert result.iloc[: period - 1].isna().all()
    assert result.iloc[period - 1:].notna().all()


def test_macd_outputs_share_index_and_are_float() -> None:
    """MACD line, signal, and histogram align to close index."""
    data = _ohlcv(40)
    params = {"fast": 12, "slow": 26, "signal": 9}
    line = macd_line(data["close"], **params)
    signal = macd_signal(data["close"], **params)
    hist = macd_histogram(data["close"], **params)
    for series in (line, signal, hist):
        assert series.index.equals(data["close"].index)
        assert series.dtype == float


def test_bb_outputs_share_index_and_middle_is_between_bands() -> None:
    """Bollinger middle lies between upper and lower where all are defined."""
    data = _ohlcv(40)
    upper = bb_upper(data["close"], period=20, std=2.0)
    middle = bb_middle(data["close"], period=20, std=2.0)
    lower = bb_lower(data["close"], period=20, std=2.0)
    valid = upper.notna() & middle.notna() & lower.notna()
    assert (upper[valid] >= middle[valid]).all()
    assert (middle[valid] >= lower[valid]).all()


def test_bb_invalid_std_raises_value_error() -> None:
    """Bollinger Bands reject non-positive std dev multiplier."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="std must be > 0"):
        bb_upper(data["close"], std=0)


@pytest.mark.parametrize("fn", [atr, adx])
def test_hlc_indicators_return_aligned_series(fn: object) -> None:
    """ATR and ADX return float Series aligned to close index."""
    data = _ohlcv(40)
    result = fn(data["close"], high=data["high"], low=data["low"], period=14)  # type: ignore[operator]
    assert result.index.equals(data["close"].index)
    assert result.dtype == float


def test_stoch_k_and_d_return_aligned_series() -> None:
    """Stochastic %K and %D align to close and stay in [0, 100] when defined."""
    data = _ohlcv(40)
    k = stoch_k(data["close"], high=data["high"], low=data["low"])
    d = stoch_d(data["close"], high=data["high"], low=data["low"])
    for series in (k, d):
        assert series.index.equals(data["close"].index)
        defined = series.dropna()
        assert (defined >= 0).all()
        assert (defined <= 100).all()


def test_obv_returns_cumulative_volume_direction_series() -> None:
    """OBV returns a float Series aligned to close."""
    data = _ohlcv()
    result = obv(data["close"], volume=data["volume"])
    assert result.index.equals(data["close"].index)
    assert result.dtype == float
    assert result.notna().all()


def test_volume_passthrough_returns_raw_volume() -> None:
    """VOLUME passthrough returns the input volume unchanged."""
    data = _ohlcv()
    result = volume_passthrough(data["volume"])
    pd.testing.assert_series_equal(result, data["volume"].astype(float))


def test_tier1_registry_has_sixteen_keys() -> None:
    """Tier 1 ships 16 registry keys (multi-output indicators count separately)."""
    assert len(INDICATORS) == 16


@pytest.mark.parametrize("name", list(INDICATORS.keys()))
def test_tier1_registry_key_has_meta_and_callable(name: str) -> None:
    """Every Tier 1 registry key has metadata and a callable wrapper."""
    assert name in INDICATOR_META
    assert callable(INDICATORS[name])
