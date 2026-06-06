"""
Central indicator registry.

Each output series is its own registry key (D-32). The signal evaluator imports
INDICATORS and INDICATOR_META from here rather than maintaining a local dict.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

import pandas as pd

from indicators.custom.chandelier import chandelier
from indicators.custom.cmf import cmf
from indicators.custom.donchian import donchian_lower, donchian_middle, donchian_upper
from indicators.custom.hull import hma
from indicators.custom.ichimoku import (
    ichimoku_chikou,
    ichimoku_kijun,
    ichimoku_senkou_a,
    ichimoku_senkou_b,
    ichimoku_tenkan,
)
from indicators.custom.keltner import keltner_lower, keltner_middle, keltner_upper
from indicators.custom.momentum import ao, qstick, tsi
from indicators.custom.pivots import pivot_p, pivot_r1, pivot_r2, pivot_r3, pivot_s1, pivot_s2, pivot_s3
from indicators.custom.supertrend import supertrend
from indicators.custom.volatility import histvol, volatility_oscillator, volrank
from indicators.custom.volume_indexes import nvi, pvi, volosc
from indicators.custom.vwap import vwap
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

ICHIMOKU_SHARED = ("tenkan", "kijun", "senkou_b", "displacement")
KELTNER_SHARED = ("period", "multiplier")
DONCHIAN_SHARED = ("period",)
PIVOT_SHARED: tuple[str, ...] = ()


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
    "SUPERTREND": supertrend,
    "VWAP": vwap,
    "HMA": hma,
    "KELTNER_UPPER": keltner_upper,
    "KELTNER_MIDDLE": keltner_middle,
    "KELTNER_LOWER": keltner_lower,
    "DONCHIAN_UPPER": donchian_upper,
    "DONCHIAN_MIDDLE": donchian_middle,
    "DONCHIAN_LOWER": donchian_lower,
    "ICHIMOKU_TENKAN": ichimoku_tenkan,
    "ICHIMOKU_KIJUN": ichimoku_kijun,
    "ICHIMOKU_SENKOU_A": ichimoku_senkou_a,
    "ICHIMOKU_SENKOU_B": ichimoku_senkou_b,
    "ICHIMOKU_CHIKOU": ichimoku_chikou,
    "PIVOT_P": pivot_p,
    "PIVOT_R1": pivot_r1,
    "PIVOT_R2": pivot_r2,
    "PIVOT_R3": pivot_r3,
    "PIVOT_S1": pivot_s1,
    "PIVOT_S2": pivot_s2,
    "PIVOT_S3": pivot_s3,
    "CHANDELIER": chandelier,
    "HISTVOL": histvol,
    "VOLRANK": volrank,
    "VOLOSC": volosc,
    "NVI": nvi,
    "PVI": pvi,
    "TSI": tsi,
    "AO": ao,
    "QSTICK": qstick,
    "VOLOSCILLATOR": volatility_oscillator,
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
    "SUPERTREND": {"inputs": ["high", "low", "close"], "shared_params": ("period", "multiplier")},
    "VWAP": {"inputs": ["high", "low", "close", "volume"], "shared_params": ("period", "variant")},
    "HMA": {"inputs": ["close"]},
    "KELTNER_UPPER": {"inputs": ["high", "low", "close"], "shared_params": KELTNER_SHARED},
    "KELTNER_MIDDLE": {"inputs": ["high", "low", "close"], "shared_params": KELTNER_SHARED},
    "KELTNER_LOWER": {"inputs": ["high", "low", "close"], "shared_params": KELTNER_SHARED},
    "DONCHIAN_UPPER": {"inputs": ["high", "low", "close"], "shared_params": DONCHIAN_SHARED},
    "DONCHIAN_MIDDLE": {"inputs": ["high", "low", "close"], "shared_params": DONCHIAN_SHARED},
    "DONCHIAN_LOWER": {"inputs": ["high", "low", "close"], "shared_params": DONCHIAN_SHARED},
    "ICHIMOKU_TENKAN": {"inputs": ["high", "low", "close"], "shared_params": ICHIMOKU_SHARED},
    "ICHIMOKU_KIJUN": {"inputs": ["high", "low", "close"], "shared_params": ICHIMOKU_SHARED},
    "ICHIMOKU_SENKOU_A": {"inputs": ["high", "low", "close"], "shared_params": ICHIMOKU_SHARED},
    "ICHIMOKU_SENKOU_B": {"inputs": ["high", "low", "close"], "shared_params": ICHIMOKU_SHARED},
    "ICHIMOKU_CHIKOU": {"inputs": ["high", "low", "close"], "shared_params": ICHIMOKU_SHARED},
    "PIVOT_P": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_R1": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_R2": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_R3": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_S1": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_S2": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "PIVOT_S3": {"inputs": ["high", "low", "close"], "shared_params": PIVOT_SHARED},
    "CHANDELIER": {"inputs": ["high", "low", "close"], "shared_params": ("period", "multiplier")},
    "HISTVOL": {"inputs": ["close"], "shared_params": ("period", "annualization")},
    "VOLRANK": {"inputs": ["high", "low", "close"], "shared_params": ("period", "atr_period")},
    "VOLOSC": {"inputs": ["close", "volume"], "shared_params": ("short_period", "long_period")},
    "NVI": {"inputs": ["close", "volume"]},
    "PVI": {"inputs": ["close", "volume"]},
    "TSI": {"inputs": ["close"], "shared_params": ("long_period", "short_period")},
    "AO": {"inputs": ["high", "low", "close"], "shared_params": ("fast_period", "slow_period")},
    "QSTICK": {"inputs": ["close", "open"]},
    "VOLOSCILLATOR": {"inputs": ["close"], "shared_params": ("short_period", "long_period")},
}
