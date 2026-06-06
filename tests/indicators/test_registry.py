"""
Tests for the central indicator registry.
"""

import pandas as pd
import pytest

from indicators.registry import INDICATOR_META, INDICATORS


def _sample_ohlcv(length: int = 30) -> pd.DataFrame:
    """Minimal OHLCV frame for registry smoke tests."""
    index = pd.date_range("2024-01-01", periods=length, freq="D", tz="UTC")
    close = pd.Series([100.0 + i for i in range(length)], index=index)
    return pd.DataFrame(
        {
            "close": close,
            "high": close + 2.0,
            "low": close - 2.0,
            "volume": 1000.0 + close,
        }
    )


def test_registry_keys_match_meta() -> None:
    """Every registered indicator has matching metadata."""
    assert set(INDICATORS.keys()) == set(INDICATOR_META.keys())


def test_registry_has_no_duplicate_keys() -> None:
    """Registry keys are unique (dict invariant)."""
    keys = list(INDICATORS.keys())
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("name", list(INDICATORS.keys()))
def test_registry_callables_return_series(name: str) -> None:
    """Each registered indicator is callable and returns a Series."""
    candles = _sample_ohlcv()
    fn = INDICATORS[name]
    meta = INDICATOR_META[name]
    kwargs: dict[str, object] = {}
    if name in {"SMA", "EMA", "WMA", "ROC"}:
        kwargs["period"] = 5
    elif name == "RSI":
        kwargs["period"] = 5
    elif name.startswith("MACD"):
        kwargs.update({"fast": 12, "slow": 26, "signal": 9})
    elif name.startswith("BB_") or name == "BBP":
        kwargs.update({"period": 5, "std": 2.0})
    elif name in {"ATR", "ADX", "CCI", "WILLR", "MFI", "CMF"}:
        kwargs["period"] = 5
    elif name.startswith("STOCH_"):
        kwargs.update({"fastk_period": 5, "slowk_period": 3, "slowd_period": 3})
    elif name.startswith("STOCHRSI"):
        kwargs.update({"period": 14, "fastk_period": 3, "fastd_period": 3})
    elif name == "STDDEV":
        kwargs.update({"period": 5, "nbdev": 1.0})

    inputs = meta["inputs"]
    if "close" in inputs:
        series_args = {col: candles[col] for col in inputs if col != "close"}
        result = fn(candles["close"], **series_args, **kwargs)
        index = candles["close"].index
    else:
        series_args = {col: candles[col] for col in inputs}
        result = fn(**series_args, **kwargs)
        index = candles[inputs[0]].index

    assert isinstance(result, pd.Series)
    assert result.index.equals(index)
