"""
Extensible overlay compute for replay buffers.

v1 wraps ``IndicatorService`` for indicator overlays. Future overlay types
(signals, chart patterns) plug in here without changing tick-slice logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from api.schemas.indicators import IndicatorSpec
from api.services.chart_data_service import indicator_series_id
from api.services.indicator_service import IndicatorService, max_warmup_bars


@dataclass(frozen=True)
class OverlayResult:
    """
    Precomputed overlay values aligned to an OHLCV frame.

    Attributes:
        overlays: Map of series id (e.g. ``RSI_14``) to per-row values.
    """

    overlays: dict[str, list[float | None]]


class OverlaySpec(Protocol):
    """Protocol for overlay specifications (indicators in v1)."""

    key: str
    params: dict[str, Any]


class OverlayPipeline:
    """
    Batch-compute chart overlays when a replay buffer loads or extends.

    Overlays are computed once per buffer segment; tick emission slices
    precomputed arrays (O(1) per bar).
    """

    def __init__(self, indicator_service: IndicatorService | None = None) -> None:
        """
        Args:
            indicator_service: Indicator compute service (default: new instance).
        """
        self._indicators = indicator_service or IndicatorService()

    def warmup_bars(self, specs: list[IndicatorSpec], timeframe: str) -> int:
        """
        Return the warmup lookback required before the first visible bar.

        Args:
            specs: Indicator specifications.
            timeframe: Bar resolution used for warmup calculation.

        Returns:
            Number of extra bars to load before the replay window.
        """
        return max_warmup_bars(specs, timeframe)

    def compute(self, frame: pd.DataFrame, specs: list[IndicatorSpec]) -> OverlayResult:
        """
        Batch-compute all overlays for the full OHLCV frame.

        Args:
            frame: OHLCV DataFrame with a ``ts`` column.
            specs: Indicator specifications.

        Returns:
            Overlay arrays keyed by stable series id, index-aligned to ``frame``.
        """
        if frame.empty or not specs:
            return OverlayResult(overlays={})

        series_list = self._indicators.compute_on_dataframe(frame, specs)
        overlays: dict[str, list[float | None]] = {}
        frame_len = len(frame)
        for series in series_list:
            series_id = indicator_series_id(series.key, series.params)
            values: list[float | None] = [None] * frame_len
            for idx, point in enumerate(series.points):
                if idx < frame_len:
                    values[idx] = point.value
            overlays[series_id] = values
        return OverlayResult(overlays=overlays)

    def compute_append(
        self,
        frame: pd.DataFrame,
        specs: list[IndicatorSpec],
        existing: dict[str, list[float | None]],
        append_from_idx: int,
    ) -> dict[str, list[float | None]]:
        """
        Extend overlay arrays after new OHLCV rows are appended.

        Recomputes on the full frame (indicators need history) but preserves
        values before ``append_from_idx`` from ``existing``.

        Args:
            frame: Full OHLCV frame including newly appended rows.
            specs: Indicator specifications.
            existing: Prior overlay arrays before append.
            append_from_idx: First new row index in ``frame``.

        Returns:
            Merged overlay arrays covering the full frame length.
        """
        if append_from_idx <= 0 or not specs:
            return self.compute(frame, specs).overlays

        fresh = self.compute(frame, specs).overlays
        merged: dict[str, list[float | None]] = {}
        for series_id, new_values in fresh.items():
            prior = list(existing.get(series_id, []))
            if len(prior) < append_from_idx:
                prior.extend([None] * (append_from_idx - len(prior)))
            merged[series_id] = prior[:append_from_idx] + new_values[append_from_idx:]
        return merged
