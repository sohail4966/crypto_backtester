"""
Rolling in-memory OHLCV + precomputed overlay buffer for replay.

Layout at cursor position (defaults):

    [ warmup ] [ trail: up to 500 bars ] [ prefetch: up to 1000 bars ahead ]
                        ↑
                   cursor (last revealed bar)

Tick emission reads precomputed overlay arrays — no per-tick indicator recompute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from api.schemas.candles import Bar
from api.schemas.indicators import IndicatorSpec
from api.services.candle_service import _ts_to_unix
from api.services.overlay_pipeline import OverlayPipeline
from indicators.warmup import frame_window_indices


@dataclass
class ReplayTick:
    """
    One replay tick emitted to the client.

    Attributes:
        bar: OHLCV bar revealed at this step.
        indicators: Map of series id to ``{time, value}`` for this bar.
    """

    bar: Bar
    indicators: dict[str, dict[str, Any]]


@dataclass
class ReplayBuffer:
    """
    Precomputed rolling buffer for O(1) tick slicing.

    Attributes:
        frame: OHLCV DataFrame including warmup bars.
        overlays: Precomputed indicator values per series id.
        window_start_idx: First visible bar index in ``frame``.
        cursor_idx: Last revealed bar index (-1 before first step).
        prefetch_end_idx: Last bar with precomputed overlays.
        latest_available_ts: Latest candle in DB for this symbol+timeframe.
    """

    frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    overlays: dict[str, list[float | None]] = field(default_factory=dict)
    window_start_idx: int = 0
    cursor_idx: int = -1
    prefetch_end_idx: int = -1
    latest_available_ts: int | None = None

    @property
    def cursor_ts(self) -> int | None:
        """
        Unix time of the last revealed bar.

        Returns:
            Bar open time at ``cursor_idx``, or ``None`` before the first step.
        """
        if self.cursor_idx < 0 or self.frame.empty:
            return None
        return _ts_to_unix(self.frame.iloc[self.cursor_idx]["ts"])

    def load(
        self,
        frame: pd.DataFrame,
        specs: list[IndicatorSpec],
        *,
        start_anchor: int,
        cursor_ts: int,
        pipeline: OverlayPipeline,
        latest_available_ts: int | None,
        visible_from_ts: int | None = None,
    ) -> None:
        """
        Initialize or replace buffer contents from a loaded OHLCV frame.

        Args:
            frame: Full frame including warmup bars before the visible window.
            specs: Indicator specifications to precompute.
            start_anchor: User-selected replay start (unix seconds).
            cursor_ts: Last revealed bar time (one bar before ``start_anchor``
                on a fresh session).
            pipeline: Overlay compute pipeline.
            latest_available_ts: Latest stored candle for open-ended end detection.
            visible_from_ts: First visible bar time; defaults to ``start_anchor``.
                Use the seek target when reloading after a far seek.
        """
        self.frame = frame.reset_index(drop=True)
        self.latest_available_ts = latest_available_ts
        if self.frame.empty:
            self.overlays = {}
            self.window_start_idx = 0
            self.cursor_idx = -1
            self.prefetch_end_idx = -1
            return

        unix_times = [_ts_to_unix(ts) for ts in self.frame["ts"]]
        visible_from = visible_from_ts if visible_from_ts is not None else start_anchor
        window_start, _ = frame_window_indices(unix_times, visible_from, unix_times[-1])
        self.window_start_idx = max(window_start, 0) if window_start >= 0 else 0
        self.prefetch_end_idx = len(self.frame) - 1
        self.overlays = pipeline.compute(self.frame, specs).overlays

        self.cursor_idx = -1
        for idx, ts in enumerate(unix_times):
            if ts <= cursor_ts:
                self.cursor_idx = idx
            else:
                break
        if self.cursor_idx < self.window_start_idx - 1:
            self.cursor_idx = self.window_start_idx - 1

    def trim_trail(self, max_trail: int, warmup_bars: int = 0) -> None:
        """
        Drop bars older than ``max_trail`` behind the cursor.

        Keeps at least ``warmup_bars`` before the cursor so indicator lookback
        remains valid after trim.

        Args:
            max_trail: Maximum visible bars to retain behind cursor.
            warmup_bars: Minimum bars to keep before cursor for indicator seeding.
        """
        if self.cursor_idx < 0 or max_trail <= 0:
            return
        trail_cutoff = max(self.window_start_idx, self.cursor_idx - max_trail + 1)
        warmup_cutoff = max(0, self.cursor_idx - warmup_bars + 1) if warmup_bars > 0 else 0
        visible_start = max(trail_cutoff, warmup_cutoff)
        if visible_start <= 0:
            return
        self.frame = self.frame.iloc[visible_start:].reset_index(drop=True)
        drop = visible_start
        self.overlays = {
            series_id: values[drop:] for series_id, values in self.overlays.items()
        }
        self.window_start_idx = max(0, self.window_start_idx - drop)
        self.cursor_idx -= drop
        self.prefetch_end_idx -= drop

    def append_frame(
        self,
        new_rows: pd.DataFrame,
        specs: list[IndicatorSpec],
        pipeline: OverlayPipeline,
    ) -> None:
        """
        Append OHLCV rows and extend overlay arrays (forward buffer extend).

        Args:
            new_rows: Additional candles fetched from the database.
            specs: Indicator specifications.
            pipeline: Overlay compute pipeline.
        """
        if new_rows.empty:
            return
        append_from = len(self.frame)
        self.frame = pd.concat([self.frame, new_rows], ignore_index=True)
        self.prefetch_end_idx = len(self.frame) - 1
        self.overlays = pipeline.compute_append(
            self.frame,
            specs,
            self.overlays,
            append_from,
        )

    def needs_extend(self, threshold: int) -> bool:
        """
        Check whether forward extend should be triggered.

        Args:
            threshold: Start extend when cursor is within this many bars of
                ``prefetch_end_idx``.

        Returns:
            ``True`` when more DB candles exist and cursor is near prefetch edge.
        """
        if self.prefetch_end_idx < 0:
            return False
        if self.latest_available_ts is None:
            return False
        last_ts = _ts_to_unix(self.frame.iloc[self.prefetch_end_idx]["ts"])
        if last_ts >= self.latest_available_ts:
            return False
        return self.cursor_idx >= self.prefetch_end_idx - threshold

    def at_latest(self) -> bool:
        """
        Check whether the cursor has reached the latest stored candle.

        Returns:
            ``True`` when ``cursor_ts`` equals ``latest_available_ts``.
        """
        if self.latest_available_ts is None or self.cursor_idx < 0:
            return False
        return self.cursor_ts == self.latest_available_ts

    def can_step(self) -> bool:
        """
        Check whether another forward step is possible.

        Returns:
            ``False`` when at latest candle or cursor has consumed prefetch.
        """
        if self.frame.empty:
            return False
        if self.latest_available_ts is None:
            return False
        if self.at_latest():
            return False
        return self.cursor_idx < self.prefetch_end_idx

    def index_at_or_before(self, ts: int) -> int:
        """
        Find the frame index of the bar at or before a unix timestamp.

        Args:
            ts: Target bar time (unix seconds).

        Returns:
            Frame index, or ``-1`` when no bar is at or before ``ts``.
        """
        for idx in range(len(self.frame) - 1, -1, -1):
            if _ts_to_unix(self.frame.iloc[idx]["ts"]) <= ts:
                return idx
        return -1

    def _bar_at(self, idx: int) -> Bar:
        """Convert a frame row to a chart ``Bar``."""
        row = self.frame.iloc[idx]
        return Bar(
            time=_ts_to_unix(row["ts"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )

    def slice_tick(self, idx: int) -> ReplayTick:
        """
        Build one tick from precomputed overlay arrays (O(1)).

        Args:
            idx: Frame index of the bar to emit.

        Returns:
            Bar plus indicator points for that index.
        """
        bar = self._bar_at(idx)
        indicators: dict[str, dict[str, Any]] = {}
        for series_id, values in self.overlays.items():
            if idx < len(values):
                indicators[series_id] = {"time": bar.time, "value": values[idx]}
        return ReplayTick(bar=bar, indicators=indicators)

    def slice_ticks(self, count: int) -> list[ReplayTick]:
        """
        Advance the cursor and return up to ``count`` ticks.

        Args:
            count: Maximum bars to reveal (minimum 1 when stepping).

        Returns:
            Ticks for newly revealed bars; may be shorter than ``count`` at end.
        """
        ticks: list[ReplayTick] = []
        for _ in range(max(1, count)):
            if not self.can_step():
                break
            self.cursor_idx += 1
            ticks.append(self.slice_tick(self.cursor_idx))
        return ticks

    def seek_to_index(self, idx: int) -> None:
        """
        Move cursor to a frame index without reloading the buffer.

        Args:
            idx: Target frame index (clamped to not precede visible window).
        """
        min_idx = self.window_start_idx - 1
        self.cursor_idx = max(idx, min_idx)

    def snapshot_bars(self) -> list[Bar]:
        """
        Return all revealed bars from window start through cursor.

        Used for WS ``snapshot`` on connect, reconnect, or seek reload.

        Returns:
            OHLCV bars in the current trail window.
        """
        if self.cursor_idx < self.window_start_idx:
            return []
        end = max(self.cursor_idx, self.window_start_idx)
        return [self._bar_at(i) for i in range(self.window_start_idx, end + 1)]

    def snapshot_indicators(self) -> dict[str, list[dict[str, Any]]]:
        """
        Return indicator series from window start through cursor.

        Returns:
            Map of series id to ``[{time, value}, ...]`` points.
        """
        if self.cursor_idx < self.window_start_idx:
            return {}
        result: dict[str, list[dict[str, Any]]] = {}
        for series_id, values in self.overlays.items():
            points: list[dict[str, Any]] = []
            for idx in range(self.window_start_idx, self.cursor_idx + 1):
                if idx < len(values) and values[idx] is not None:
                    points.append(
                        {
                            "time": _ts_to_unix(self.frame.iloc[idx]["ts"]),
                            "value": values[idx],
                        }
                    )
            result[series_id] = points
        return result

    def buffer_end_ts(self) -> int | None:
        """
        Unix time of the last bar currently loaded in the buffer.

        Returns:
            Prefetch edge timestamp, or ``None`` when buffer is empty.
        """
        if self.frame.empty or self.prefetch_end_idx < 0:
            return None
        return _ts_to_unix(self.frame.iloc[self.prefetch_end_idx]["ts"])

    def queue_remaining(self) -> int:
        """
        Count bars pre-sliced and ready to stream ahead of the cursor.

        Reported in WS ``tick_batch`` as ``queueRemaining`` so the client
        knows when to send ``refill``.

        Returns:
            Bars between cursor and prefetch end (inclusive of next step).
        """
        if self.cursor_idx < 0:
            return max(0, self.prefetch_end_idx - self.window_start_idx + 1)
        return max(0, self.prefetch_end_idx - self.cursor_idx)
