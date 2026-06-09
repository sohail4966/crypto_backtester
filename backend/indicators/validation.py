"""
Shared parameter validation for indicator wrappers.
"""

from __future__ import annotations

import pandas as pd


def validate_period(period: int, *, min_val: int, series: pd.Series) -> None:
    """
    Validate a lookback period against bounds and series length.

    Args:
        period: Requested lookback length in bars.
        min_val: Minimum allowed period (inclusive).
        series: Input price or value series.

    Raises:
        ValueError: If period is below min_val or the series is too short.
    """
    if period < min_val:
        raise ValueError(f"period must be >= {min_val}, got {period}")
    if len(series) < period:
        raise ValueError(f"series length {len(series)} is shorter than period {period}")
