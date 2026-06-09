"""
Buy-and-hold benchmark helpers (D-42).
"""

from __future__ import annotations

import pandas as pd


def compute_buy_and_hold_return(candles: pd.DataFrame) -> float:
    """
    Compute total buy-and-hold return from the first to last close in the window.

    Args:
        candles: OHLCV DataFrame with close column.

    Returns:
        Total return as a decimal (e.g. 0.25 for +25%).
    """
    if len(candles) < 2:
        return 0.0

    start_price = float(candles.iloc[0]["close"])
    end_price = float(candles.iloc[-1]["close"])
    if start_price <= 0.0:
        return 0.0
    return (end_price / start_price) - 1.0
