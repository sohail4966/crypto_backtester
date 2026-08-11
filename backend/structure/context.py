"""
Multi-timeframe structure context with HTF trend forward-fill (D-58).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from structure.labels import DEFAULT_EQ_TOLERANCE_PCT
from structure.levels import DEFAULT_LEVEL_COUNT
from structure.ohlcv import candle_timestamps
from structure.pipeline import analyze_structure
from structure.swings import DEFAULT_LEFT_BARS, DEFAULT_RIGHT_BARS
from structure.types import StructureResult, Trend


@dataclass(frozen=True)
class StructureContext:
    """
    Base-timeframe structure plus higher-timeframe results and aligned trends.

    ``htf_trend_on_base`` maps each HTF name to a Trend Series indexed like the
    base candle ``ts`` (as-of forward-fill, no lookahead).
    """

    base_tf: str
    base: StructureResult
    higher: dict[str, StructureResult]
    htf_trend_on_base: dict[str, pd.Series]

    @classmethod
    def from_frames(
        cls,
        base_tf: str,
        base_df: pd.DataFrame,
        higher_frames: Mapping[str, pd.DataFrame],
        *,
        left_bars: int = DEFAULT_LEFT_BARS,
        right_bars: int = DEFAULT_RIGHT_BARS,
        tolerance_pct: float = DEFAULT_EQ_TOLERANCE_PCT,
        k: int = DEFAULT_LEVEL_COUNT,
        confirmed_only: bool = False,
    ) -> StructureContext:
        """
        Build context from in-memory OHLCV frames (pure; no DB).

        Args:
            base_tf: Name of the base timeframe (e.g. ``1h``).
            base_df: Base OHLCV candles.
            higher_frames: Mapping of HTF name → OHLCV frame (up to two typical).
            left_bars: Pivot left width.
            right_bars: Pivot right width.
            tolerance_pct: EQ tolerance.
            k: S/R count.
            confirmed_only: Passed through to per-TF analysis.

        Returns:
            Populated ``StructureContext``.

        Raises:
            ValueError: If base or any HTF frame is empty.
        """
        if base_df.empty:
            raise ValueError(f"empty candles for base timeframe {base_tf!r}")
        for tf, frame in higher_frames.items():
            if frame.empty:
                raise ValueError(f"empty candles for timeframe {tf!r}")

        params = {
            "left_bars": left_bars,
            "right_bars": right_bars,
            "tolerance_pct": tolerance_pct,
            "k": k,
            "confirmed_only": confirmed_only,
        }
        base = analyze_structure(base_df, **params)
        higher: dict[str, StructureResult] = {
            tf: analyze_structure(frame, **params) for tf, frame in higher_frames.items()
        }
        base_index = pd.DatetimeIndex(candle_timestamps(base_df))
        htf_trend_on_base = {
            tf: _forward_fill_trend(result.trend, base_index) for tf, result in higher.items()
        }
        return cls(
            base_tf=base_tf,
            base=base,
            higher=higher,
            htf_trend_on_base=htf_trend_on_base,
        )

    @classmethod
    def load(
        cls,
        symbol: str,
        base_tf: str,
        htf_tfs: Sequence[str],
        start: str,
        end: str,
        *,
        left_bars: int = DEFAULT_LEFT_BARS,
        right_bars: int = DEFAULT_RIGHT_BARS,
        tolerance_pct: float = DEFAULT_EQ_TOLERANCE_PCT,
        k: int = DEFAULT_LEVEL_COUNT,
        confirmed_only: bool = False,
    ) -> StructureContext:
        """
        Load candles via ``get_candles`` and build a multi-TF structure context.

        Args:
            symbol: Trading pair, e.g. ``BTC/USDT``.
            base_tf: Base timeframe.
            htf_tfs: Higher timeframes (typically two, e.g. ``4h``, ``1d``).
            start: Inclusive ISO start date.
            end: Inclusive ISO end date.
            left_bars: Pivot left width.
            right_bars: Pivot right width.
            tolerance_pct: EQ tolerance.
            k: S/R count.
            confirmed_only: Passed through to per-TF analysis.

        Returns:
            Populated ``StructureContext``.

        Raises:
            ValueError: If any requested series is empty.

        Side effects:
            Reads from the database through ``data.loader.get_candles``.
        """
        from data.loader import get_candles

        base_df = get_candles(symbol, base_tf, start, end)
        higher_frames = {tf: get_candles(symbol, tf, start, end) for tf in htf_tfs}
        return cls.from_frames(
            base_tf,
            base_df,
            higher_frames,
            left_bars=left_bars,
            right_bars=right_bars,
            tolerance_pct=tolerance_pct,
            k=k,
            confirmed_only=confirmed_only,
        )


def _forward_fill_trend(htf_trend: pd.Series, base_index: pd.DatetimeIndex) -> pd.Series:
    """As-of forward-fill an HTF trend Series onto the base timestamp index."""
    if htf_trend.empty:
        return pd.Series(Trend.UNDEFINED, index=base_index, dtype=object)
    aligned = htf_trend.copy()
    aligned.index = pd.DatetimeIndex(aligned.index)
    if aligned.index.tz is None:
        aligned.index = aligned.index.tz_localize("UTC")
    else:
        aligned.index = aligned.index.tz_convert("UTC")
    aligned = aligned[~aligned.index.duplicated(keep="last")].sort_index()
    return aligned.reindex(base_index, method="ffill").fillna(Trend.UNDEFINED)
