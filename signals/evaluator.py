"""
Evaluate a strategy dict into entry/exit boolean Series.

Pure with respect to the database: operates only on an in-memory candle DataFrame.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from exceptions import InvalidSignalError
from indicators.registry import INDICATORS
from signals.types import SignalCondition, Strategy

OPS: dict[str, Callable[[pd.Series, float], pd.Series]] = {
    "<": lambda series, threshold: series < threshold,
    "<=": lambda series, threshold: series <= threshold,
    ">": lambda series, threshold: series > threshold,
    ">=": lambda series, threshold: series >= threshold,
    "==": lambda series, threshold: series == threshold,
}


def _resolve_indicator(candles: pd.DataFrame, condition: SignalCondition) -> pd.Series:
    """
    Compute the indicator series for a single condition leg.

    Args:
        candles: OHLCV DataFrame with a close column.
        condition: Signal condition specifying indicator name and params.

    Returns:
        Indicator values aligned to candles.

    Raises:
        InvalidSignalError: If the indicator name is not registered.
    """
    # Case-insensitive so YAML can use "RSI" or "rsi" without duplicate registry keys.
    name = condition["indicator"].upper()
    if name not in INDICATORS:
        raise InvalidSignalError(f"Unknown indicator: {condition['indicator']}")

    params = condition.get("params", {})
    indicator_fn = INDICATORS[name]
    return indicator_fn(candles["close"], **params)


def _evaluate_condition(candles: pd.DataFrame, condition: SignalCondition) -> pd.Series:
    """
    Evaluate one condition leg to a boolean Series.

    Args:
        candles: OHLCV DataFrame.
        condition: Signal condition with op and value threshold.

    Returns:
        Boolean Series; NaN indicator values are treated as False.

    Raises:
        InvalidSignalError: If the operator is not supported.
    """
    series = _resolve_indicator(candles, condition)
    op = condition["op"]
    if op not in OPS:
        raise InvalidSignalError(f"Unknown operator: {op}")
    threshold = condition["value"]
    result = OPS[op](series, threshold)
    # Warmup NaNs are not tradable signals — treat as False, not "unknown".
    return result.fillna(False)


def evaluate_signals(
    candles: pd.DataFrame,
    strategy: Strategy,
) -> tuple[pd.Series, pd.Series]:
    """
    Evaluate entry and exit conditions for a long-only strategy dict.

    Args:
        candles: OHLCV DataFrame used for indicator computation.
        strategy: Dict with entry and exit SignalCondition legs.

    Returns:
        Tuple of (entry_signals, exit_signals) boolean Series aligned to candles.
    """
    entry = _evaluate_condition(candles, strategy["entry"])
    exit_ = _evaluate_condition(candles, strategy["exit"])
    return entry, exit_
