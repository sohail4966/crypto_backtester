"""
Named SMC signal conditions for the strategy evaluator.
"""

from __future__ import annotations

import pandas as pd

from exceptions import InvalidSignalError
from smc.config import SmcConfig
from smc.pipeline import analyze_smc
from smc.structure_view import event_index, prepare_ohlcv
from smc.types import SmcConcept


def evaluate_smc_leg(candles: pd.DataFrame, condition: dict) -> pd.Series:
    """
    Evaluate a ``{"smc": "<concept>", ...}`` condition to a boolean Series.

    Supported keys:
      - ``smc`` (required): concept name
      - ``side``: ``bullish`` | ``bearish`` | ``any`` (default)
      - ``params``: optional ``SmcConfig`` field overrides
    """
    if "smc" not in condition:
        raise InvalidSignalError("SMC condition missing required key: smc")

    try:
        concept = SmcConcept(str(condition["smc"]).lower())
    except ValueError as exc:
        raise InvalidSignalError(f"Unknown smc concept: {condition['smc']!r}") from exc

    side = str(condition.get("side", "any")).lower()
    if side not in {"bullish", "bearish", "any"}:
        raise InvalidSignalError(f"Unknown smc side: {side!r}")

    try:
        config = SmcConfig.from_params(condition.get("params"))
    except ValueError as exc:
        raise InvalidSignalError(str(exc)) from exc

    frame = prepare_ohlcv(candles)
    if frame.empty:
        return pd.Series(dtype=bool)

    result = analyze_smc(frame, config)
    series = result.series_for(event_index(frame), concept, side=side)
    # Align to caller index when possible.
    if len(series) == len(candles.index):
        series.index = candles.index
    return series.fillna(False).astype(bool)
