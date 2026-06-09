"""
Chaikin Money Flow — custom implementation (TA-Lib ADOSC is not CMF).
"""

from __future__ import annotations

import pandas as pd

from indicators.validation import validate_period

DEFAULT_CMF_PERIOD = 20


def cmf(
    close: pd.Series,
    *,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    period: int = DEFAULT_CMF_PERIOD,
) -> pd.Series:
    """
    Chaikin Money Flow over a rolling window (TradingView-aligned).

    Money Flow Multiplier (MFM) = ((close - low) - (high - close)) / (high - low).
    When high equals low, MFM is 0. CMF = sum(MFM * volume) / sum(volume) over period.
    """
    validate_period(period, min_val=1, series=close)
    if len(volume) != len(close):
        raise ValueError("volume series length must match close series length")

    hl_range = high - low
    mfm = pd.Series(0.0, index=close.index, dtype=float)
    in_range = hl_range != 0
    mfm[in_range] = ((close[in_range] - low[in_range]) - (high[in_range] - close[in_range])) / hl_range[
        in_range
    ]

    money_flow_volume = mfm * volume
    cmf_values = money_flow_volume.rolling(window=period, min_periods=period).sum() / volume.rolling(
        window=period, min_periods=period
    ).sum()
    return cmf_values.astype(float)
