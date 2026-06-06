"""
Central indicator registry.

Each output series is its own registry key (D-32). The signal evaluator imports
INDICATORS and INDICATOR_META from here rather than maintaining a local dict.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

import pandas as pd

from indicators.custom.cmf import cmf
from indicators.talib_wrappers import (
    ad,
    adx,
    atr,
    bb_lower,
    bb_middle,
    bb_upper,
    bbp,
    cci,
    ema,
    macd_histogram,
    macd_line,
    macd_signal,
    mfi,
    obv,
    roc,
    rsi,
    sar,
    sma,
    stddev,
    stoch_d,
    stoch_k,
    stochrsi_d,
    stochrsi_k,
    volume_passthrough,
    willr,
    wma,
)

IndicatorFn = Callable[..., pd.Series]


class IndicatorMeta(TypedDict, total=False):
    """Metadata describing which OHLCV columns an indicator consumes."""

    inputs: list[str]
    shared_params: tuple[str, ...]


INDICATORS: dict[str, IndicatorFn] = {
    "SMA": sma,
    "EMA": ema,
    "WMA": wma,
    "MACD_LINE": macd_line,
    "MACD_SIGNAL": macd_signal,
    "MACD_HIST": macd_histogram,
    "RSI": rsi,
    "BB_UPPER": bb_upper,
    "BB_MIDDLE": bb_middle,
    "BB_LOWER": bb_lower,
    "ATR": atr,
    "ADX": adx,
    "STOCH_K": stoch_k,
    "STOCH_D": stoch_d,
    "OBV": obv,
    "VOLUME": volume_passthrough,
    "MFI": mfi,
    "SAR": sar,
    "STOCHRSI_K": stochrsi_k,
    "STOCHRSI_D": stochrsi_d,
    "CCI": cci,
    "WILLR": willr,
    "ROC": roc,
    "STDDEV": stddev,
    "AD": ad,
    "CMF": cmf,
    "BBP": bbp,
}

INDICATOR_META: dict[str, IndicatorMeta] = {
    "SMA": {"inputs": ["close"]},
    "EMA": {"inputs": ["close"]},
    "WMA": {"inputs": ["close"]},
    "MACD_LINE": {"inputs": ["close"], "shared_params": ("fast", "slow", "signal")},
    "MACD_SIGNAL": {"inputs": ["close"], "shared_params": ("fast", "slow", "signal")},
    "MACD_HIST": {"inputs": ["close"], "shared_params": ("fast", "slow", "signal")},
    "RSI": {"inputs": ["close"]},
    "BB_UPPER": {"inputs": ["close"], "shared_params": ("period", "std")},
    "BB_MIDDLE": {"inputs": ["close"], "shared_params": ("period", "std")},
    "BB_LOWER": {"inputs": ["close"], "shared_params": ("period", "std")},
    "ATR": {"inputs": ["high", "low", "close"]},
    "ADX": {"inputs": ["high", "low", "close"]},
    "STOCH_K": {
        "inputs": ["high", "low", "close"],
        "shared_params": ("fastk_period", "slowk_period", "slowd_period"),
    },
    "STOCH_D": {
        "inputs": ["high", "low", "close"],
        "shared_params": ("fastk_period", "slowk_period", "slowd_period"),
    },
    "OBV": {"inputs": ["close", "volume"]},
    "VOLUME": {"inputs": ["volume"]},
    "MFI": {"inputs": ["high", "low", "close", "volume"]},
    "SAR": {"inputs": ["high", "low"], "shared_params": ("acceleration", "maximum")},
    "STOCHRSI_K": {
        "inputs": ["close"],
        "shared_params": ("period", "fastk_period", "fastd_period"),
    },
    "STOCHRSI_D": {
        "inputs": ["close"],
        "shared_params": ("period", "fastk_period", "fastd_period"),
    },
    "CCI": {"inputs": ["high", "low", "close"]},
    "WILLR": {"inputs": ["high", "low", "close"]},
    "ROC": {"inputs": ["close"]},
    "STDDEV": {"inputs": ["close"], "shared_params": ("period", "nbdev")},
    "AD": {"inputs": ["high", "low", "close", "volume"]},
    "CMF": {"inputs": ["high", "low", "close", "volume"]},
    "BBP": {"inputs": ["close"], "shared_params": ("period", "std")},
}
