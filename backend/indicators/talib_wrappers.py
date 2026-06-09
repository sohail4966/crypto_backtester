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
DEFAULT_MFI_PERIOD = 14
DEFAULT_SAR_ACCELERATION = 0.02
DEFAULT_SAR_MAXIMUM = 0.2
DEFAULT_STOCHRSI_PERIOD = 14
DEFAULT_STOCHRSI_FASTK = 5
DEFAULT_STOCHRSI_FASTD = 3
DEFAULT_CCI_PERIOD = 14
DEFAULT_WILLR_PERIOD = 14
DEFAULT_ROC_PERIOD = 10
DEFAULT_STDDEV_PERIOD = 5
DEFAULT_STDDEV_NBDEV = 1.0


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


def mfi(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    period: int = DEFAULT_MFI_PERIOD,
) -> pd.Series:
    """Money Flow Index via TA-Lib (requires high, low, close, volume)."""
    validate_period(period, min_val=2, series=close)
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    result = talib.MFI(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        _float64_array(volume),
        timeperiod=period,
    )
    return _series_from_talib(close, result)


def sar(
    high: pd.Series,
    low: pd.Series,
    *,
    acceleration: float = DEFAULT_SAR_ACCELERATION,
    maximum: float = DEFAULT_SAR_MAXIMUM,
) -> pd.Series:
    """Parabolic SAR via TA-Lib."""
    if len(high) < 2:
        raise ValueError(f"series length {len(high)} is shorter than minimum 2")
    if acceleration <= 0:
        raise ValueError(f"acceleration must be > 0, got {acceleration}")
    if maximum <= 0:
        raise ValueError(f"maximum must be > 0, got {maximum}")
    result = talib.SAR(
        _float64_array(high),
        _float64_array(low),
        acceleration=acceleration,
        maximum=maximum,
    )
    return _series_from_talib(high, result)


def _stochrsi_arrays(
    close: pd.Series,
    *,
    period: int = DEFAULT_STOCHRSI_PERIOD,
    fastk_period: int = DEFAULT_STOCHRSI_FASTK,
    fastd_period: int = DEFAULT_STOCHRSI_FASTD,
) -> tuple[np.ndarray, np.ndarray]:
    validate_period(period, min_val=2, series=close)
    validate_period(fastk_period, min_val=1, series=close)
    validate_period(fastd_period, min_val=1, series=close)
    return talib.STOCHRSI(
        _float64_array(close),
        timeperiod=period,
        fastk_period=fastk_period,
        fastd_period=fastd_period,
    )


def stochrsi_k(
    close: pd.Series,
    *,
    period: int = DEFAULT_STOCHRSI_PERIOD,
    fastk_period: int = DEFAULT_STOCHRSI_FASTK,
    fastd_period: int = DEFAULT_STOCHRSI_FASTD,
) -> pd.Series:
    """Stochastic RSI %K via TA-Lib."""
    fastk, _ = _stochrsi_arrays(
        close, period=period, fastk_period=fastk_period, fastd_period=fastd_period
    )
    return _series_from_talib(close, fastk)


def stochrsi_d(
    close: pd.Series,
    *,
    period: int = DEFAULT_STOCHRSI_PERIOD,
    fastk_period: int = DEFAULT_STOCHRSI_FASTK,
    fastd_period: int = DEFAULT_STOCHRSI_FASTD,
) -> pd.Series:
    """Stochastic RSI %D via TA-Lib."""
    _, fastd = _stochrsi_arrays(
        close, period=period, fastk_period=fastk_period, fastd_period=fastd_period
    )
    return _series_from_talib(close, fastd)


def cci(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_CCI_PERIOD,
) -> pd.Series:
    """Commodity Channel Index via TA-Lib."""
    validate_period(period, min_val=2, series=close)
    result = talib.CCI(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        timeperiod=period,
    )
    return _series_from_talib(close, result)


def willr(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    period: int = DEFAULT_WILLR_PERIOD,
) -> pd.Series:
    """Williams %R via TA-Lib."""
    validate_period(period, min_val=2, series=close)
    result = talib.WILLR(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        timeperiod=period,
    )
    return _series_from_talib(close, result)


def roc(close: pd.Series, period: int = DEFAULT_ROC_PERIOD) -> pd.Series:
    """Rate of Change via TA-Lib."""
    validate_period(period, min_val=1, series=close)
    result = talib.ROC(_float64_array(close), timeperiod=period)
    return _series_from_talib(close, result)


def stddev(
    close: pd.Series,
    *,
    period: int = DEFAULT_STDDEV_PERIOD,
    nbdev: float = DEFAULT_STDDEV_NBDEV,
) -> pd.Series:
    """Rolling standard deviation via TA-Lib."""
    validate_period(period, min_val=2, series=close)
    if nbdev <= 0:
        raise ValueError(f"nbdev must be > 0, got {nbdev}")
    result = talib.STDDEV(
        _float64_array(close),
        timeperiod=period,
        nbdev=nbdev,
    )
    return _series_from_talib(close, result)


def ad(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """Accumulation/Distribution line via TA-Lib."""
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")
    result = talib.AD(
        _float64_array(high),
        _float64_array(low),
        _float64_array(close),
        _float64_array(volume),
    )
    return _series_from_talib(close, result)


def bbp(
    close: pd.Series,
    *,
    period: int = DEFAULT_BB_PERIOD,
    std: float = DEFAULT_BB_STD,
) -> pd.Series:
    """
    Bollinger Band %B derived from TA-Lib BBANDS.

    %B = (close - lower) / (upper - lower). Returns NaN when band width is zero.
    """
    upper, _, lower = _bbands_arrays(close, period=period, std=std)
    upper_s = _series_from_talib(close, upper)
    lower_s = _series_from_talib(close, lower)
    width = upper_s - lower_s
    percent_b = pd.Series(float("nan"), index=close.index, dtype=float)
    valid = width != 0
    percent_b[valid] = (close[valid] - lower_s[valid]) / width[valid]
    return percent_b
