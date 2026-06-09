"""
Tests for Tier 2 TA-Lib wrappers and derived indicators (Step 4).
"""

import pandas as pd
import pytest

from indicators.custom.cmf import cmf
from indicators.registry import INDICATOR_META, INDICATORS
from indicators.talib_wrappers import (
    ad,
    bbp,
    cci,
    roc,
    sar,
    stddev,
    stochrsi_d,
    stochrsi_k,
    willr,
)

TIER2_TALIB_KEYS = {
    "SAR",
    "STOCHRSI_K",
    "STOCHRSI_D",
    "CCI",
    "WILLR",
    "MFI",
    "ROC",
    "STDDEV",
    "AD",
    "CMF",
    "BBP",
}


def _ohlcv(length: int = 40) -> dict[str, pd.Series]:
    """Synthetic OHLCV series long enough for Tier 2 warmup."""
    index = pd.date_range("2024-01-01", periods=length, freq="D", tz="UTC")
    close = pd.Series([100.0 + i * 0.5 for i in range(length)], index=index)
    return {
        "close": close,
        "high": close + 2.0,
        "low": close - 2.0,
        "volume": pd.Series([1000.0 + i * 10 for i in range(length)], index=index),
    }


def test_tier2_talib_registry_keys_present() -> None:
    """Tier 2 TA-Lib batch registry keys are all registered."""
    assert TIER2_TALIB_KEYS <= set(INDICATORS.keys())


@pytest.mark.parametrize("name", sorted(TIER2_TALIB_KEYS))
def test_tier2_registry_key_has_meta_and_callable(name: str) -> None:
    """Every Tier 2 key has metadata and a callable wrapper."""
    assert name in INDICATOR_META
    assert callable(INDICATORS[name])


def test_sar_returns_aligned_series() -> None:
    """Parabolic SAR aligns to high/low index."""
    data = _ohlcv()
    result = sar(data["high"], data["low"])
    assert result.index.equals(data["high"].index)
    assert result.dtype == float


def test_sar_invalid_acceleration_raises_value_error() -> None:
    """SAR rejects non-positive acceleration."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="acceleration must be > 0"):
        sar(data["high"], data["low"], acceleration=0)


def test_stochrsi_k_and_d_stay_in_range_when_defined() -> None:
    """Stochastic RSI outputs are in [0, 100] where defined."""
    data = _ohlcv(60)
    k = stochrsi_k(data["close"], period=14, fastk_period=3, fastd_period=3)
    d = stochrsi_d(data["close"], period=14, fastk_period=3, fastd_period=3)
    for series in (k, d):
        defined = series.dropna()
        assert (defined >= 0).all()
        assert (defined <= 100).all()


@pytest.mark.parametrize("fn", [cci, willr])
def test_hlc_momentum_indicators_return_aligned_series(fn: object) -> None:
    """CCI and Williams %R return float Series aligned to close."""
    data = _ohlcv()
    result = fn(data["close"], high=data["high"], low=data["low"], period=14)  # type: ignore[operator]
    assert result.index.equals(data["close"].index)
    assert result.dtype == float


def test_willr_values_are_non_positive_when_defined() -> None:
    """Williams %R ranges from -100 to 0."""
    data = _ohlcv()
    result = willr(data["close"], high=data["high"], low=data["low"], period=14)
    defined = result.dropna()
    assert (defined <= 0).all()
    assert (defined >= -100).all()


def test_roc_returns_aligned_series() -> None:
    """ROC returns float Series aligned to close."""
    data = _ohlcv()
    result = roc(data["close"], period=10)
    assert result.index.equals(data["close"].index)
    assert result.dtype == float
    assert result.iloc[:10].isna().all()


def test_stddev_invalid_nbdev_raises_value_error() -> None:
    """STDDEV rejects non-positive nbdev multiplier."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="nbdev must be > 0"):
        stddev(data["close"], period=5, nbdev=0)


def test_ad_returns_aligned_cumulative_series() -> None:
    """Accumulation/Distribution line aligns to close."""
    data = _ohlcv()
    result = ad(
        data["close"],
        high=data["high"],
        low=data["low"],
        volume=data["volume"],
    )
    assert result.index.equals(data["close"].index)
    assert result.dtype == float
    assert result.notna().all()


def test_cmf_period_3_hand_calculated() -> None:
    """CMF(3) on a short flat-range series matches manual calculation."""
    close = pd.Series([10.0, 11.0, 12.0, 13.0])
    high = pd.Series([10.0, 11.0, 12.0, 13.0])
    low = pd.Series([10.0, 11.0, 12.0, 13.0])
    volume = pd.Series([100.0, 100.0, 100.0, 100.0])
    result = cmf(close, high=high, low=low, volume=volume, period=3)
    assert result.iloc[2:].eq(0.0).all()


def test_cmf_invalid_period_raises_value_error() -> None:
    """CMF rejects non-positive period."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="period must be >= 1"):
        cmf(data["close"], high=data["high"], low=data["low"], volume=data["volume"], period=0)


def test_bbp_is_between_zero_and_one_when_inside_bands() -> None:
    """%B lies between 0 and 1 when price is within Bollinger Bands."""
    data = _ohlcv(40)
    result = bbp(data["close"], period=20, std=2.0)
    defined = result.dropna()
    assert (defined >= 0).all()
    assert (defined <= 1).all()
