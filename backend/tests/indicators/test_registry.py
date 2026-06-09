"""
Tests for the central indicator registry.
"""

import pandas as pd
import pytest

from indicators.registry import INDICATOR_META, INDICATORS


def _sample_ohlcv(length: int = 60) -> pd.DataFrame:
    """Minimal OHLCV frame for registry smoke tests."""
    index = pd.date_range("2024-01-01", periods=length, freq="D", tz="UTC")
    close = pd.Series([100.0 + i for i in range(length)], index=index)
    return pd.DataFrame(
        {
            "close": close,
            "open": close - 0.5,
            "high": close + 2.0,
            "low": close - 2.0,
            "volume": 1000.0 + close,
        }
    )


def _registry_kwargs(name: str) -> dict[str, object]:
    """Default params for registry smoke tests."""
    if name in {"SMA", "EMA", "WMA", "ROC", "HMA"}:
        return {"period": 5}
    if name == "RSI":
        return {"period": 5}
    if name.startswith("MACD"):
        return {"fast": 12, "slow": 26, "signal": 9}
    if name.startswith("BB_") or name == "BBP":
        return {"period": 5, "std": 2.0}
    if name in {"ATR", "ADX", "CCI", "WILLR", "MFI", "CMF", "CHANDELIER"}:
        return {"period": 5}
    if name == "SUPERTREND":
        return {"period": 5, "multiplier": 2.0}
    if name.startswith("STOCH_"):
        return {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3}
    if name.startswith("STOCHRSI"):
        return {"period": 14, "fastk_period": 3, "fastd_period": 3}
    if name == "STDDEV":
        return {"period": 5, "nbdev": 1.0}
    if name.startswith("KELTNER"):
        return {"period": 5, "multiplier": 2.0}
    if name.startswith("DONCHIAN"):
        return {"period": 5}
    if name.startswith("ICHIMOKU"):
        return {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26}
    if name == "VWAP":
        return {"period": 5, "variant": "rolling"}
    if name == "HISTVOL":
        return {"period": 5, "annualization": 252.0}
    if name == "VOLRANK":
        return {"period": 20, "atr_period": 5}
    if name in {"VOLOSC", "VOLOSCILLATOR"}:
        return {"short_period": 3, "long_period": 5}
    if name == "TSI":
        return {"long_period": 10, "short_period": 5}
    if name == "AO":
        return {"fast_period": 3, "slow_period": 5}
    if name == "QSTICK":
        return {"period": 5}
    return {}


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
    kwargs = _registry_kwargs(name)

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
