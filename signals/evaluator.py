"""
Evaluate a strategy dict into entry/exit boolean Series.

Pure with respect to the database: operates only on an in-memory candle DataFrame.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from exceptions import InvalidSignalError
from indicators.registry import INDICATOR_META, INDICATORS, IndicatorFn, IndicatorMeta
from signals.types import DualStrategy, EntryTrigger, IndicatorRef, SignalCondition, Strategy

DEFAULT_ENTRY_TRIGGER: EntryTrigger = "edge"

OPS: dict[str, Callable[[pd.Series, float], pd.Series]] = {
    "<": lambda series, threshold: series < threshold,
    "<=": lambda series, threshold: series <= threshold,
    ">": lambda series, threshold: series > threshold,
    ">=": lambda series, threshold: series >= threshold,
    "==": lambda series, threshold: series == threshold,
}

OPS_SERIES: dict[str, Callable[[pd.Series, pd.Series], pd.Series]] = {
    "<": lambda left, right: left < right,
    "<=": lambda left, right: left <= right,
    ">": lambda left, right: left > right,
    ">=": lambda left, right: left >= right,
    "==": lambda left, right: left == right,
}


def _call_indicator(
    fn: IndicatorFn,
    candles: pd.DataFrame,
    meta: IndicatorMeta,
    params: dict,
) -> pd.Series:
    """
    Route OHLCV columns to an indicator per INDICATOR_META (D-31).

    Close is passed as the first positional argument when required; other inputs
    are keyword arguments derived from the candle DataFrame.
    """
    inputs = meta["inputs"]
    kwargs = {col: candles[col] for col in inputs if col != "close"}
    if "close" in inputs:
        return fn(candles["close"], **kwargs, **params)
    return fn(**kwargs, **params)


def _resolve_compare_series(candles: pd.DataFrame, compare: str | IndicatorRef) -> pd.Series:
    """
    Resolve the right-hand side of a cross-comparison condition.

    Supports comparing against close or another registered indicator.
    """
    if compare == "close":
        return candles["close"]

    if isinstance(compare, dict) and "indicator" in compare:
        ref: SignalCondition = {
            "indicator": compare["indicator"],
            "op": ">",
            "value": 0.0,
        }
        if "params" in compare:
            ref["params"] = compare["params"]
        return _resolve_indicator(candles, ref)

    raise InvalidSignalError(f"Invalid compare reference: {compare!r}")


def _resolve_indicator(candles: pd.DataFrame, condition: SignalCondition) -> pd.Series:
    """
    Compute the indicator series for a single condition leg.

    Args:
        candles: OHLCV DataFrame.
        condition: Signal condition specifying indicator name and params.

    Returns:
        Indicator values aligned to candles.

    Raises:
        InvalidSignalError: If the indicator name is not registered or params are invalid.
    """
    # Case-insensitive so YAML can use "RSI" or "rsi" without duplicate registry keys.
    name = condition["indicator"].upper()
    if name not in INDICATORS:
        raise InvalidSignalError(f"Unknown indicator: {condition['indicator']}")

    params = condition.get("params", {})
    indicator_fn = INDICATORS[name]
    try:
        return _call_indicator(indicator_fn, candles, INDICATOR_META[name], params)
    except ValueError as exc:
        raise InvalidSignalError(str(exc)) from exc


def _evaluate_condition(candles: pd.DataFrame, condition: SignalCondition) -> pd.Series:
    """
    Evaluate one condition leg to a boolean Series.

    Supports a single indicator leg or an AND group via `all`.

    Args:
        candles: OHLCV DataFrame.
        condition: Signal condition with op and value threshold, or nested `all`.

    Returns:
        Boolean Series; NaN indicator values are treated as False.

    Raises:
        InvalidSignalError: If the operator is not supported or the condition is invalid.
    """
    if "all" in condition:
        if not condition["all"]:
            raise InvalidSignalError("Condition group 'all' must contain at least one leg")
        combined = pd.Series(True, index=candles.index)
        for leg in condition["all"]:
            combined &= _evaluate_condition(candles, leg)
        return combined

    required = ("indicator", "op")
    if "compare" not in condition:
        required = (*required, "value")
    missing = [key for key in required if key not in condition]
    if missing:
        raise InvalidSignalError(f"Condition missing required keys: {', '.join(missing)}")

    series = _resolve_indicator(candles, condition)
    op = condition["op"]
    if "compare" in condition:
        if op not in OPS_SERIES:
            raise InvalidSignalError(f"Unknown operator: {op}")
        rhs = _resolve_compare_series(candles, condition["compare"])
        result = OPS_SERIES[op](series, rhs)
    else:
        if op not in OPS:
            raise InvalidSignalError(f"Unknown operator: {op}")
        threshold = condition["value"]
        result = OPS[op](series, threshold)
    # Warmup NaNs are not tradable signals — treat as False, not "unknown".
    return result.fillna(False)


def edge_trigger(level: pd.Series) -> pd.Series:
    """
    Convert a level-triggered boolean series to edge-triggered (OQ-21).

    Fires only on bars where the condition becomes true after being false.
    """
    previous = level.shift(1, fill_value=False).astype(bool)
    return level & ~previous


def apply_entry_trigger(level: pd.Series, mode: EntryTrigger) -> pd.Series:
    """Apply edge or level semantics to entry signals."""
    if mode == "level":
        return level
    if mode == "edge":
        return edge_trigger(level)
    raise InvalidSignalError(f"Unknown entry_trigger: {mode!r}")


def _resolve_entry_trigger(strategy: Strategy | DualStrategy) -> EntryTrigger:
    """Return configured entry trigger mode; defaults to edge."""
    mode = str(strategy.get("entry_trigger", DEFAULT_ENTRY_TRIGGER))
    if mode not in {"edge", "level"}:
        raise InvalidSignalError(f"Unknown entry_trigger: {mode!r}")
    return mode  # type: ignore[return-value]


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
    entry_mode = _resolve_entry_trigger(strategy)
    entry = apply_entry_trigger(_evaluate_condition(candles, strategy["entry"]), entry_mode)
    exit_ = _evaluate_condition(candles, strategy["exit"])
    return entry, exit_


def evaluate_dual_strategy(
    candles: pd.DataFrame,
    strategy: DualStrategy,
) -> dict[str, pd.Series]:
    """
    Evaluate long and short entry/exit conditions for a dual-side strategy.

    Args:
        candles: OHLCV DataFrame used for indicator computation.
        strategy: Dict with long and short SideStrategy blocks.

    Returns:
        Dict with long_entry, long_exit, short_entry, and short_exit boolean Series.
    """
    entry_mode = _resolve_entry_trigger(strategy)
    return {
        "long_entry": apply_entry_trigger(
            _evaluate_condition(candles, strategy["long"]["entry"]),
            entry_mode,
        ),
        "long_exit": _evaluate_condition(candles, strategy["long"]["exit"]),
        "short_entry": apply_entry_trigger(
            _evaluate_condition(candles, strategy["short"]["entry"]),
            entry_mode,
        ),
        "short_exit": _evaluate_condition(candles, strategy["short"]["exit"]),
    }
