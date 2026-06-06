"""
TA-Lib-backed indicator wrappers.

Each function is a pure wrapper: validate params, call TA-Lib, return a pandas Series
with the input index preserved.
"""

from __future__ import annotations

import talib
import numpy as np
import pandas as pd

from indicators.validation import validate_period

DEFAULT_RSI_PERIOD = 14
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_BB_PERIOD = 20
DEFAULT_BB_STD = 2.0
DEFAULT_ATR_PERIOD = 14
DEFAULT_ADX_PERIOD = 14
DEFAULT_STOCH_FASTK = 5
DEFAULT_STOCH_SLOWK = 3
DEFAULT_STOCH_SLOWD = 3


def _float64_array(values: pd.Series) -> np.ndarray:
    """Convert a Series to float64 for TA-Lib (requires double precision)."""
    return np.asarray(values, dtype=np.float64)


def _series_from_talib(values: pd.Series, output: pd.ArrayLike) -> pd.Series:
    """Wrap a TA-Lib ndarray output as a float Series aligned to values.index."""
    return pd.Series(output, index=values.index, dtype=float)


def sma(close: pd.Series, period: int) -> pd.Series:
    """
    Compute a simple moving average of closing prices via TA-Lib.

    Args:
        close: Closing price series.
        period: Rolling window length in bars.

    Returns:
        SMA values; first (period - 1) rows are NaN.

    Raises:
        ValueError: If period is less than 1 or the series is shorter than period.
    """
    validate_period(period, min_val=1, series=close)
    result = talib.SMA(_float64_array(close), timeperiod=period)
    return _series_from_talib(close, result)


def rsi(close: pd.Series, period: int = DEFAULT_RSI_PERIOD) -> pd.Series:
    """
    Compute RSI via TA-Lib (Wilder's smoothing).

    Args:
        close: Closing price series, indexed by datetime.
        period: Lookback period. Default is 14.

    Returns:
        RSI values as a float Series in the range [0, 100].
        Leading warmup rows are NaN until TA-Lib seeds the average.

    Raises:
        ValueError: If period is less than 2 or the series is shorter than period.
    """
    validate_period(period, min_val=2, series=close)
    result = talib.RSI(_float64_array(close), timeperiod=period)
    return _series_from_talib(close, result)


def ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential moving average of closing prices via TA-Lib."""
    validate_period(period, min_val=1, series=close)
    result = talib.EMA(_float64_array(close), timeperiod=period)
    return _series_from_talib(close, result)


def wma(close: pd.Series, period: int) -> pd.Series:
    """Weighted moving average of closing prices via TA-Lib."""
    validate_period(period, min_val=1, series=close)
    result = talib.WMA(_float64_array(close), timeperiod=period)
    return _series_from_talib(close, result)


def _macd_arrays(
    close: pd.Series,
    *,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    validate_period(fast, min_val=2, series=close)
    validate_period(slow, min_val=2, series=close)
    validate_period(signal, min_val=1, series=close)
    return talib.MACD(
        _float64_array(close),
        fastperiod=fast,
        slowperiod=slow,
        signalperiod=signal,
    )


def macd_line(
    close: pd.Series,
    *,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> pd.Series:
    """MACD line (fast EMA minus slow EMA) via TA-Lib."""
    line, _, _ = _macd_arrays(close, fast=fast, slow=slow, signal=signal)
    return _series_from_talib(close, line)


def macd_signal(
    close: pd.Series,
    *,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> pd.Series:
    """MACD signal line (EMA of MACD line) via TA-Lib."""
    _, signal_line, _ = _macd_arrays(close, fast=fast, slow=slow, signal=signal)
    return _series_from_talib(close, signal_line)


def macd_histogram(
    close: pd.Series,
    *,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> pd.Series:
    """MACD histogram (MACD line minus signal line) via TA-Lib."""
    _, _, hist = _macd_arrays(close, fast=fast, slow=slow, signal=signal)
    return _series_from_talib(close, hist)


def _bbands_arrays(
    close: pd.Series,
    *,
    period: int = DEFAULT_BB_PERIOD,
    std: float = DEFAULT_BB_STD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    validate_period(period, min_val=2, series=close)
    if std <= 0:
        raise ValueError(f"std must be > 0, got {std}")
    return talib.BBANDS(
        _float64_array(close),
        timeperiod=period,
        nbdevup=std,
        nbdevdn=std,
        matype=0,
    )


def bb_upper(
    close: pd.Series,
    *,
    period: int = DEFAULT_BB_PERIOD,
    std: float = DEFAULT_BB_STD,
) -> pd.Series:
    """Bollinger Band upper band via TA-Lib."""
    upper, _, _ = _bbands_arrays(close, period=period, std=std)
    return _series_from_talib(close, upper)


def bb_middle(
    close: pd.Series,
    *,
    period: int = DEFAULT_BB_PERIOD,
    std: float = DEFAULT_BB_STD,
) -> pd.Series:
    """Bollinger Band middle band (SMA) via TA-Lib."""
    _, middle, _ = _bbands_arrays(close, period=period, std=std)
    return _series_from_talib(close, middle)


def bb_lower(
    close: pd.Series,
    *,
    period: int = DEFAULT_BB_PERIOD,
    std: float = DEFAULT_BB_STD,
) -> pd.Series:
    """Bollinger Band lower band via TA-Lib."""
    _, _, lower = _bbands_arrays(close, period=period, std=std)
    return _series_from_talib(close, lower)


def atr(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_ATR_PERIOD,
) -> pd.Series:
    """Average True Range via TA-Lib."""
    validate_period(period, min_val=1, series=close)
    result = talib.ATR(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        timeperiod=period,
    )
    return _series_from_talib(close, result)


def adx(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_ADX_PERIOD,
) -> pd.Series:
    """Average Directional Index via TA-Lib."""
    validate_period(period, min_val=2, series=close)
    result = talib.ADX(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        timeperiod=period,
    )
    return _series_from_talib(close, result)


def _stoch_arrays(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    fastk_period: int = DEFAULT_STOCH_FASTK,
    slowk_period: int = DEFAULT_STOCH_SLOWK,
    slowd_period: int = DEFAULT_STOCH_SLOWD,
) -> tuple[np.ndarray, np.ndarray]:
    validate_period(fastk_period, min_val=1, series=close)
    validate_period(slowk_period, min_val=1, series=close)
    validate_period(slowd_period, min_val=1, series=close)
    return talib.STOCH(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        fastk_period=fastk_period,
        slowk_period=slowk_period,
        slowk_matype=0,
        slowd_period=slowd_period,
        slowd_matype=0,
    )


def stoch_k(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    fastk_period: int = DEFAULT_STOCH_FASTK,
    slowk_period: int = DEFAULT_STOCH_SLOWK,
    slowd_period: int = DEFAULT_STOCH_SLOWD,
) -> pd.Series:
    """Stochastic %K via TA-Lib."""
    slowk, _ = _stoch_arrays(
        close,
        high=high,
        low=low,
        fastk_period=fastk_period,
        slowk_period=slowk_period,
        slowd_period=slowd_period,
    )
    return _series_from_talib(close, slowk)


def stoch_d(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    fastk_period: int = DEFAULT_STOCH_FASTK,
    slowk_period: int = DEFAULT_STOCH_SLOWK,
    slowd_period: int = DEFAULT_STOCH_SLOWD,
) -> pd.Series:
    """Stochastic %D via TA-Lib."""
    _, slowd = _stoch_arrays(
        close,
        high=high,
        low=low,
        fastk_period=fastk_period,
        slowk_period=slowk_period,
        slowd_period=slowd_period,
    )
    return _series_from_talib(close, slowd)


def obv(close: pd.Series, *, volume: pd.Series) -> pd.Series:
    """On Balance Volume via TA-Lib."""
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    result = talib.OBV(_float64_array(close), _float64_array(volume))
    return _series_from_talib(close, result)


def volume_passthrough(volume: pd.Series) -> pd.Series:
    """Return raw volume as a float Series (registry passthrough)."""
    return volume.astype(float)
