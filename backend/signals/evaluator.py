"""
Evaluate a strategy dict into entry/exit boolean Series.

Pure with respect to the database: operates only on in-memory candle DataFrames.
Phase 9 extends the grammar with nested AND/OR/NOT, SEQUENCE, multi-TF, lookbacks,
and named pattern leaves.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from dsl.align import _ensure_datetime_index, align_series_to_base, resample_ohlcv
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

_GROUP_OPS = frozenset({"AND", "OR", "NOT", "SEQUENCE"})
_OHLCV_FIELDS = frozenset({"open", "high", "low", "close", "volume"})


@dataclass
class EvalContext:
    """Evaluation context for multi-TF frames and caches."""

    base_timeframe: str
    base_frame: pd.DataFrame
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    frames_explicit: bool = False
    _pattern_signals: dict[str, pd.Series] | None = field(default=None, repr=False)


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


def _shift_series(series: pd.Series, bars_ago: int) -> pd.Series:
    """Shift a series backward by ``bars_ago`` bars (lookback)."""
    if bars_ago < 0:
        raise InvalidSignalError("bars_ago must be >= 0")
    if bars_ago == 0:
        return series
    return series.shift(bars_ago)


def _resolve_field_series(candles: pd.DataFrame, field_name: str, bars_ago: int = 0) -> pd.Series:
    """Resolve an OHLCV column with optional lookback."""
    name = field_name.lower()
    if name not in _OHLCV_FIELDS:
        raise InvalidSignalError(f"Unknown field: {field_name!r}")
    if name not in candles.columns:
        raise InvalidSignalError(f"candles missing column: {name}")
    return _shift_series(candles[name], bars_ago)


def _resolve_compare_series(
    candles: pd.DataFrame,
    compare: str | IndicatorRef | Mapping,
) -> pd.Series:
    """
    Resolve the right-hand side of a cross-comparison condition.

    Supports comparing against close or another registered indicator.
    """
    if compare == "close":
        return candles["close"]

    if isinstance(compare, Mapping) and "indicator" in compare:
        bars_ago = int(compare.get("bars_ago", 0) or 0)
        series = _resolve_indicator(
            candles,
            {
                "indicator": compare["indicator"],
                "op": ">",
                "value": 0.0,
                **({"params": compare["params"]} if "params" in compare else {}),
            },
        )
        return _shift_series(series, bars_ago)

    raise InvalidSignalError(f"Invalid compare reference: {compare!r}")


def _resolve_ref_series(candles: pd.DataFrame, ref: Mapping) -> pd.Series:
    """Resolve a ``ref`` lookback operand (field or indicator)."""
    bars_ago = int(ref.get("bars_ago", 0) or 0)
    if "field" in ref and ref["field"] is not None:
        return _resolve_field_series(candles, str(ref["field"]), bars_ago)
    if "indicator" in ref and ref["indicator"] is not None:
        series = _resolve_indicator(
            candles,
            {
                "indicator": ref["indicator"],
                "op": ">",
                "value": 0.0,
                **({"params": ref["params"]} if "params" in ref else {}),
            },
        )
        return _shift_series(series, bars_ago)
    raise InvalidSignalError(f"Invalid ref: {ref!r}")


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


def _frame_for_timeframe(ctx: EvalContext, timeframe: str | None) -> pd.DataFrame:
    """Return the OHLCV frame for a condition timeframe."""
    if timeframe is None:
        return ctx.base_frame
    if timeframe in ctx.frames:
        return _ensure_datetime_index(ctx.frames[timeframe])
    # When the caller supplied a frames map, every referenced TF must be present
    # (Phase 8 D-106 contract) — even if it matches base_timeframe by string.
    if ctx.frames_explicit:
        raise InvalidSignalError(
            f"timeframe {timeframe!r} not provided in frames"
        )
    if timeframe == ctx.base_timeframe:
        return ctx.base_frame
    # Synthesize HTF from base when caller did not supply frames (library path).
    resampled = resample_ohlcv(ctx.base_frame, timeframe)
    ctx.frames[timeframe] = resampled
    return resampled


def _align_to_base(ctx: EvalContext, series: pd.Series, timeframe: str | None) -> pd.Series:
    """Align a possibly-HTF series onto the base index without look-ahead."""
    base_index = ctx.base_frame.index
    if timeframe is None or timeframe == ctx.base_timeframe:
        out = series.copy()
        if len(out) == len(base_index):
            out.index = base_index
        else:
            out = out.reindex(base_index)
        return out
    aligned = align_series_to_base(series, base_index, timeframe)
    return aligned


def _pattern_signals(ctx: EvalContext) -> dict[str, pd.Series]:
    """Lazy-compute pattern boolean Series for the base frame."""
    if ctx._pattern_signals is None:
        from patterns.pipeline import analyze_patterns

        result = analyze_patterns(ctx.base_frame.reset_index(names="ts"))
        # analyze_patterns expects ts column; restore index alignment.
        signals: dict[str, pd.Series] = {}
        for name, series in result.signals.items():
            s = series.copy()
            if len(s) == len(ctx.base_frame.index):
                s.index = ctx.base_frame.index
            signals[name] = s.fillna(False).astype(bool)
        ctx._pattern_signals = signals
    return ctx._pattern_signals


def _evaluate_sequence(
    ctx: EvalContext,
    conditions: list[SignalCondition],
    within_bars: int,
) -> pd.Series:
    """
    Pragmatic SEQUENCE: last leg True at i, priors True at strictly increasing
    indices inside ``[i - within_bars, i)``.
    """
    if within_bars < 1:
        raise InvalidSignalError("SEQUENCE within_bars must be >= 1")
    if len(conditions) < 2:
        raise InvalidSignalError("SEQUENCE requires at least two conditions")

    legs = [_evaluate_condition(ctx, leg) for leg in conditions]
    n = len(ctx.base_frame)
    result = pd.Series(False, index=ctx.base_frame.index)

    # Precompute true indices per leg for O(n * legs) window scans.
    true_idx = [leg.to_numpy().nonzero()[0] for leg in legs]
    for i in range(n):
        if not bool(legs[-1].iloc[i]):
            continue
        window_start = max(0, i - within_bars)
        prev = window_start - 1
        ok = True
        for leg_trues in true_idx[:-1]:
            candidates = leg_trues[(leg_trues > prev) & (leg_trues < i) & (leg_trues >= window_start)]
            if len(candidates) == 0:
                ok = False
                break
            prev = int(candidates[0])
        if ok:
            result.iloc[i] = True
    return result


def _evaluate_leaf(ctx: EvalContext, condition: SignalCondition) -> pd.Series:
    """Evaluate a non-group leaf on the appropriate timeframe, then align."""
    timeframe = condition.get("timeframe")

    if "smc" in condition:
        from smc.conditions import evaluate_smc_leg

        frame = _frame_for_timeframe(ctx, timeframe)
        # SMC expects possible ts column; pass reset when index-only.
        smc_frame = frame.reset_index(names="ts") if "ts" not in frame.columns else frame
        series = evaluate_smc_leg(smc_frame, dict(condition))
        if len(series) == len(frame.index):
            series.index = frame.index
        return _align_to_base(ctx, series.fillna(False).astype(bool), timeframe)

    if "pattern" in condition:
        if timeframe is not None and timeframe != ctx.base_timeframe:
            raise InvalidSignalError("pattern conditions do not support timeframe in v1")
        name = str(condition["pattern"])
        signals = _pattern_signals(ctx)
        if name not in signals:
            # Unknown pattern → always False (still valid schema if name exists in enum;
            # runtime miss is soft-false for forward-compat). Prefer strict error:
            raise InvalidSignalError(f"Unknown pattern: {name}")
        return signals[name].fillna(False).astype(bool)

    frame = _frame_for_timeframe(ctx, timeframe)
    bars_ago = int(condition.get("bars_ago", 0) or 0)

    if "field" in condition:
        left = _resolve_field_series(frame, str(condition["field"]), bars_ago)
    elif "indicator" in condition:
        left = _shift_series(_resolve_indicator(frame, condition), bars_ago)
    else:
        raise InvalidSignalError("Condition missing indicator, field, smc, or pattern")

    op = condition["op"]
    if "ref" in condition:
        if op not in OPS_SERIES:
            raise InvalidSignalError(f"Unknown operator: {op}")
        rhs = _resolve_ref_series(frame, condition["ref"])
        result = OPS_SERIES[op](left, rhs)
    elif "compare" in condition:
        if op not in OPS_SERIES:
            raise InvalidSignalError(f"Unknown operator: {op}")
        rhs = _resolve_compare_series(frame, condition["compare"])
        result = OPS_SERIES[op](left, rhs)
    else:
        if "value" not in condition:
            raise InvalidSignalError("Condition missing required keys: value")
        if op not in OPS:
            raise InvalidSignalError(f"Unknown operator: {op}")
        result = OPS[op](left, float(condition["value"]))

    result = result.fillna(False)
    return _align_to_base(ctx, result, timeframe).fillna(False).astype(bool)


def _evaluate_condition(ctx: EvalContext, condition: SignalCondition) -> pd.Series:
    """
    Evaluate one condition leg or group to a boolean Series.

    Supports nested AND/OR/NOT/SEQUENCE, legacy ``all``, SMC, pattern, field,
    and indicator leaves (with optional timeframe / bars_ago / ref / compare).
    """
    if "all" in condition:
        if not condition["all"]:
            raise InvalidSignalError("Condition group 'all' must contain at least one leg")
        combined = pd.Series(True, index=ctx.base_frame.index)
        for leg in condition["all"]:
            combined &= _evaluate_condition(ctx, leg)
        return combined.astype(bool)

    # Phase 8 screener aliases (D-105): ``any`` / ``not`` keys alongside Phase 9 op groups.
    if "any" in condition:
        children = condition["any"]
        if not children:
            raise InvalidSignalError("Condition group 'any' must contain at least one leg")
        combined = pd.Series(False, index=ctx.base_frame.index)
        for leg in children:
            combined |= _evaluate_condition(ctx, leg)
        return combined.astype(bool)

    if "not" in condition:
        inner = condition["not"]
        if not isinstance(inner, dict):
            raise InvalidSignalError("Condition 'not' must wrap a single condition object")
        return (~_evaluate_condition(ctx, inner)).astype(bool)  # type: ignore[arg-type]

    op_raw = condition.get("op")
    if op_raw is not None and str(op_raw).upper() in _GROUP_OPS and "conditions" in condition:
        op = str(op_raw).upper()
        children = condition.get("conditions") or []
        if op == "AND":
            if not children:
                raise InvalidSignalError("AND requires at least one condition")
            combined = pd.Series(True, index=ctx.base_frame.index)
            for leg in children:
                combined &= _evaluate_condition(ctx, leg)
            return combined.astype(bool)
        if op == "OR":
            if not children:
                raise InvalidSignalError("OR requires at least one condition")
            combined = pd.Series(False, index=ctx.base_frame.index)
            for leg in children:
                combined |= _evaluate_condition(ctx, leg)
            return combined.astype(bool)
        if op == "NOT":
            if len(children) != 1:
                raise InvalidSignalError("NOT requires exactly one child condition")
            return (~_evaluate_condition(ctx, children[0])).astype(bool)
        if op == "SEQUENCE":
            within = int(condition.get("within_bars", 0) or 0)
            return _evaluate_sequence(ctx, list(children), within)

    # Legacy / leaf paths (including indicator leaves that also have op)
    if "smc" in condition or "pattern" in condition or "field" in condition or "indicator" in condition:
        # Validate required keys for classic indicator leaves without compare/ref.
        if "indicator" in condition or "field" in condition:
            if "op" not in condition:
                raise InvalidSignalError("Condition missing required keys: op")
            if "compare" not in condition and "ref" not in condition and "value" not in condition:
                if "smc" not in condition and "pattern" not in condition:
                    raise InvalidSignalError("Condition missing required keys: value")
        return _evaluate_leaf(ctx, condition)

    raise InvalidSignalError(f"Unrecognized condition shape: {sorted(condition.keys())}")


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


def _build_context(
    candles: pd.DataFrame,
    *,
    base_timeframe: str,
    frames: dict[str, pd.DataFrame] | None,
    frames_explicit: bool = False,
) -> EvalContext:
    """Normalize base candles and optional HTF frames into an EvalContext."""
    base = _ensure_datetime_index(candles)
    normalized_frames = {
        tf: _ensure_datetime_index(frame) for tf, frame in (frames or {}).items()
    }
    return EvalContext(
        base_timeframe=base_timeframe,
        base_frame=base,
        frames=normalized_frames,
        frames_explicit=frames_explicit,
    )


def evaluate_condition(
    candles: pd.DataFrame,
    condition: SignalCondition | dict,
    *,
    frames: dict[str, pd.DataFrame] | None = None,
    base_timeframe: str = "1d",
) -> pd.Series:
    """
    Evaluate a single condition tree to a boolean Series (Phase 8+ / Phase 9).

    When ``frames`` is passed (including ``{}``), every leaf ``timeframe`` must
    be present in the map. When ``frames`` is omitted, higher TFs may be
    resampled from ``candles``.

    Args:
        candles: Base OHLCV frame.
        condition: Condition tree (all/any/not or op/conditions or leaf).
        frames: Optional HTF OHLCV map.
        base_timeframe: Resolution of ``candles``.

    Returns:
        Boolean Series aligned to ``candles`` index.
    """
    explicit = frames is not None
    ctx = _build_context(
        candles,
        base_timeframe=base_timeframe,
        frames=frames,
        frames_explicit=explicit,
    )
    series = _evaluate_condition(ctx, condition)  # type: ignore[arg-type]
    series.index = candles.index
    return series.fillna(False).astype(bool)


def evaluate_signals(
    candles: pd.DataFrame,
    strategy: Strategy,
    *,
    base_timeframe: str = "1d",
    frames: dict[str, pd.DataFrame] | None = None,
) -> tuple[pd.Series, pd.Series]:
    """
    Evaluate entry and exit conditions for a long-only strategy dict.

    Args:
        candles: OHLCV DataFrame used for indicator computation.
        strategy: Dict with entry and exit SignalCondition legs.
        base_timeframe: Resolution of ``candles`` (for multi-TF alignment).
        frames: Optional map of timeframe → OHLCV for multi-TF conditions.

    Returns:
        Tuple of (entry_signals, exit_signals) boolean Series aligned to candles.
    """
    ctx = _build_context(
        candles,
        base_timeframe=base_timeframe,
        frames=frames,
        frames_explicit=frames is not None,
    )
    entry_mode = _resolve_entry_trigger(strategy)
    entry = apply_entry_trigger(_evaluate_condition(ctx, strategy["entry"]), entry_mode)
    exit_ = _evaluate_condition(ctx, strategy["exit"])
    # Preserve caller index when possible.
    entry.index = candles.index
    exit_.index = candles.index
    return entry, exit_


def evaluate_dual_strategy(
    candles: pd.DataFrame,
    strategy: DualStrategy,
    *,
    base_timeframe: str = "1d",
    frames: dict[str, pd.DataFrame] | None = None,
) -> dict[str, pd.Series]:
    """
    Evaluate long and short entry/exit conditions for a dual-side strategy.

    Args:
        candles: OHLCV DataFrame used for indicator computation.
        strategy: Dict with long and short SideStrategy blocks.
        base_timeframe: Resolution of ``candles``.
        frames: Optional HTF frames.

    Returns:
        Dict with long_entry, long_exit, short_entry, and short_exit boolean Series.
    """
    ctx = _build_context(
        candles,
        base_timeframe=base_timeframe,
        frames=frames,
        frames_explicit=frames is not None,
    )
    entry_mode = _resolve_entry_trigger(strategy)
    out = {
        "long_entry": apply_entry_trigger(
            _evaluate_condition(ctx, strategy["long"]["entry"]),
            entry_mode,
        ),
        "long_exit": _evaluate_condition(ctx, strategy["long"]["exit"]),
        "short_entry": apply_entry_trigger(
            _evaluate_condition(ctx, strategy["short"]["entry"]),
            entry_mode,
        ),
        "short_exit": _evaluate_condition(ctx, strategy["short"]["exit"]),
    }
    for series in out.values():
        series.index = candles.index
    return out
