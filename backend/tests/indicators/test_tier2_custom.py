"""
Tests for Tier 2 custom indicators (Step 5).
"""

import pandas as pd
import pytest

from indicators.custom.donchian import donchian_lower, donchian_upper
from indicators.custom.ichimoku import ichimoku_kijun, ichimoku_tenkan
from indicators.custom.momentum import ao, qstick, tsi
from indicators.custom.pivots import pivot_p, pivot_r1, pivot_s1
from indicators.custom.supertrend import supertrend
from indicators.custom.volatility import histvol, volatility_oscillator, volrank
from indicators.custom.volume_indexes import nvi, pvi, volosc
from indicators.custom.vwap import vwap
from indicators.registry import INDICATOR_META, INDICATORS

TIER2_CUSTOM_KEYS = {
    "SUPERTREND",
    "VWAP",
    "HMA",
    "KELTNER_UPPER",
    "KELTNER_MIDDLE",
    "KELTNER_LOWER",
    "DONCHIAN_UPPER",
    "DONCHIAN_MIDDLE",
    "DONCHIAN_LOWER",
    "ICHIMOKU_TENKAN",
    "ICHIMOKU_KIJUN",
    "ICHIMOKU_SENKOU_A",
    "ICHIMOKU_SENKOU_B",
    "ICHIMOKU_CHIKOU",
    "PIVOT_P",
    "PIVOT_R1",
    "PIVOT_R2",
    "PIVOT_R3",
    "PIVOT_S1",
    "PIVOT_S2",
    "PIVOT_S3",
    "CHANDELIER",
    "HISTVOL",
    "VOLRANK",
    "VOLOSC",
    "NVI",
    "PVI",
    "TSI",
    "AO",
    "QSTICK",
    "VOLOSCILLATOR",
}


def _ohlcv(length: int = 60, freq: str = "D") -> dict[str, pd.Series]:
    """Synthetic OHLCV with datetime index."""
    index = pd.date_range("2024-01-01", periods=length, freq=freq, tz="UTC")
    close = pd.Series([100.0 + i * 0.3 for i in range(length)], index=index)
    return {
        "close": close,
        "open": close - 0.5,
        "high": close + 2.0,
        "low": close - 2.0,
        "volume": pd.Series([1000.0 + i * 5 for i in range(length)], index=index),
    }


def test_tier2_custom_registry_keys_present() -> None:
    """All Step 5 custom registry keys are registered."""
    assert TIER2_CUSTOM_KEYS <= set(INDICATORS.keys())


@pytest.mark.parametrize("name", sorted(TIER2_CUSTOM_KEYS))
def test_tier2_custom_key_has_meta_and_callable(name: str) -> None:
    """Every Tier 2 custom key has metadata and a callable wrapper."""
    assert name in INDICATOR_META
    assert callable(INDICATORS[name])


def test_supertrend_returns_aligned_series() -> None:
    """SuperTrend aligns to close and produces float values after warmup."""
    data = _ohlcv(60)
    result = supertrend(
        data["close"], high=data["high"], low=data["low"], period=10, multiplier=3.0
    )
    assert result.index.equals(data["close"].index)
    assert result.dtype == float
    assert result.iloc[10:].notna().any()


def test_supertrend_invalid_multiplier_raises_value_error() -> None:
    """SuperTrend rejects non-positive multiplier."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="multiplier must be > 0"):
        supertrend(data["close"], high=data["high"], low=data["low"], multiplier=0)


def test_vwap_rolling_returns_aligned_series() -> None:
    """Rolling VWAP aligns to close index."""
    data = _ohlcv()
    result = vwap(
        data["close"],
        high=data["high"],
        low=data["low"],
        volume=data["volume"],
        period=14,
        variant="rolling",
    )
    assert result.index.equals(data["close"].index)
    assert result.iloc[13:].notna().all()


def test_vwap_session_resets_within_utc_day() -> None:
    """Session VWAP resets at each UTC calendar day."""
    index = pd.date_range("2024-01-01 00:00", periods=48, freq="h", tz="UTC")
    close = pd.Series(100.0, index=index)
    high = close + 1.0
    low = close - 1.0
    volume = pd.Series(100.0, index=index)
    result = vwap(close, high=high, low=low, volume=volume, variant="session")
    assert result.iloc[0] == pytest.approx(100.0)
    assert result.iloc[24] == pytest.approx(100.0)


def test_vwap_invalid_variant_raises_value_error() -> None:
    """VWAP rejects unknown variant."""
    data = _ohlcv()
    with pytest.raises(ValueError, match="variant must be"):
        vwap(
            data["close"],
            high=data["high"],
            low=data["low"],
            volume=data["volume"],
            variant="invalid",
        )


def test_ichimoku_tenkan_and_kijun_align_to_close() -> None:
    """Ichimoku conversion and base lines align to close index."""
    data = _ohlcv(80)
    tenkan = ichimoku_tenkan(data["close"], high=data["high"], low=data["low"], tenkan=9, kijun=26)
    kijun = ichimoku_kijun(data["close"], high=data["high"], low=data["low"], tenkan=9, kijun=26)
    assert tenkan.index.equals(data["close"].index)
    assert kijun.index.equals(data["close"].index)
    assert tenkan.iloc[8:].notna().all()
    assert kijun.iloc[25:].notna().all()


def test_donchian_upper_ge_lower_when_defined() -> None:
    """Donchian upper band is at or above lower band."""
    data = _ohlcv()
    upper = donchian_upper(data["close"], high=data["high"], low=data["low"], period=20)
    lower = donchian_lower(data["close"], high=data["high"], low=data["low"], period=20)
    valid = upper.notna() & lower.notna()
    assert (upper[valid] >= lower[valid]).all()


def test_pivot_daily_uses_prior_bar() -> None:
    """On daily data, pivot P uses prior bar H/L/C."""
    data = _ohlcv(10, freq="D")
    pivot = pivot_p(data["close"], high=data["high"], low=data["low"])
    assert pd.isna(pivot.iloc[0])
    prior_high = data["high"].iloc[1]
    prior_low = data["low"].iloc[1]
    prior_close = data["close"].iloc[1]
    assert pivot.iloc[2] == pytest.approx((prior_high + prior_low + prior_close) / 3.0)


def test_pivot_r1_and_s1_bracket_pivot_on_daily() -> None:
    """R1 and S1 derive from pivot P on daily data."""
    data = _ohlcv(10, freq="D")
    pivot = pivot_p(data["close"], high=data["high"], low=data["low"])
    r1 = pivot_r1(data["close"], high=data["high"], low=data["low"])
    s1 = pivot_s1(data["close"], high=data["high"], low=data["low"])
    valid = pivot.notna()
    assert (r1[valid] >= pivot[valid]).all()
    assert (s1[valid] <= pivot[valid]).all()


def test_histvol_is_non_negative_when_defined() -> None:
    """Historical volatility is non-negative."""
    data = _ohlcv()
    result = histvol(data["close"], period=20)
    assert result.dropna().ge(0).all()


def test_volrank_stays_in_percentile_range() -> None:
    """Volatility rank is between 0 and 100 when defined."""
    data = _ohlcv(120)
    result = volrank(data["close"], high=data["high"], low=data["low"], period=50, atr_period=14)
    defined = result.dropna()
    assert (defined >= 0).all()
    assert (defined <= 100).all()


def test_nvi_starts_at_default_and_pvi_updates_on_volume_increase() -> None:
    """NVI/PVI seed at 1000 and evolve with volume rules."""
    close = pd.Series([100.0, 101.0, 102.0, 103.0])
    volume = pd.Series([1000.0, 900.0, 1100.0, 1100.0])
    nvi_result = nvi(close, volume=volume)
    pvi_result = pvi(close, volume=volume)
    assert nvi_result.iloc[0] == pytest.approx(1000.0)
    assert pvi_result.iloc[0] == pytest.approx(1000.0)
    assert nvi_result.iloc[1] != nvi_result.iloc[0]
    assert pvi_result.iloc[2] != pvi_result.iloc[1]


def test_volosc_and_volatility_oscillator_return_aligned_series() -> None:
    """Volume and volatility oscillators align to close."""
    data = _ohlcv(60)
    vo = volosc(data["close"], volume=data["volume"], short_period=5, long_period=10)
    vol_osc = volatility_oscillator(data["close"], short_period=5, long_period=10)
    assert vo.index.equals(data["close"].index)
    assert vol_osc.index.equals(data["close"].index)


def test_ao_and_tsi_and_qstick_return_aligned_series() -> None:
    """Momentum custom indicators align to close index."""
    data = _ohlcv(60)
    ao_result = ao(data["close"], high=data["high"], low=data["low"])
    tsi_result = tsi(data["close"])
    qstick_result = qstick(data["close"], open=data["open"])
    for series in (ao_result, tsi_result, qstick_result):
        assert series.index.equals(data["close"].index)
        assert series.dtype == float
