"""
Indicator catalog and batch compute for API clients.
"""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd
import psycopg

from api.exceptions import ValidationError
from api.schemas.indicators import (
    IndicatorCatalogEntry,
    IndicatorComputeResponse,
    IndicatorPoint,
    IndicatorSeries,
    IndicatorSpec,
)
from api.services.candle_service import CandleService, _ts_to_unix
from indicators.registry import INDICATOR_META, INDICATORS
from indicators.warmup import frame_window_indices, warmup_bars

INDICATOR_DEFAULTS: dict[str, dict[str, Any]] = {
    "SMA": {"period": 14},
    "EMA": {"period": 14},
    "WMA": {"period": 14},
    "RSI": {"period": 14},
    "ATR": {"period": 14},
    "ADX": {"period": 14},
    "MACD_LINE": {"fast": 12, "slow": 26, "signal": 9},
    "MACD_SIGNAL": {"fast": 12, "slow": 26, "signal": 9},
    "MACD_HIST": {"fast": 12, "slow": 26, "signal": 9},
    "BB_UPPER": {"period": 20, "std": 2.0},
    "BB_MIDDLE": {"period": 20, "std": 2.0},
    "BB_LOWER": {"period": 20, "std": 2.0},
    "BBP": {"period": 20, "std": 2.0},
    "STOCH_K": {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3},
    "STOCH_D": {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3},
    "STOCHRSI_K": {"period": 14, "fastk_period": 5, "fastd_period": 3},
    "STOCHRSI_D": {"period": 14, "fastk_period": 5, "fastd_period": 3},
    "SAR": {"acceleration": 0.02, "maximum": 0.2},
    "CCI": {"period": 14},
    "WILLR": {"period": 14},
    "ROC": {"period": 10},
    "STDDEV": {"period": 5, "nbdev": 1.0},
    "MFI": {"period": 14},
    "CMF": {"period": 20},
    "SUPERTREND": {"period": 10, "multiplier": 3.0},
    "VWAP": {"period": 14, "variant": "rolling"},
    "HMA": {"period": 16},
    "KELTNER_UPPER": {"period": 20, "multiplier": 2.0},
    "KELTNER_MIDDLE": {"period": 20, "multiplier": 2.0},
    "KELTNER_LOWER": {"period": 20, "multiplier": 2.0},
    "DONCHIAN_UPPER": {"period": 20},
    "DONCHIAN_MIDDLE": {"period": 20},
    "DONCHIAN_LOWER": {"period": 20},
    "ICHIMOKU_TENKAN": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
    "ICHIMOKU_KIJUN": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
    "ICHIMOKU_SENKOU_A": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
    "ICHIMOKU_SENKOU_B": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
    "ICHIMOKU_CHIKOU": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
    "CHANDELIER": {"period": 22, "multiplier": 3.0},
    "HISTVOL": {"period": 20, "annualization": 252},
    "VOLRANK": {"period": 100, "atr_period": 14},
    "VOLOSC": {"short_period": 5, "long_period": 10},
    "TSI": {"long_period": 25, "short_period": 13},
    "AO": {"fast_period": 5, "slow_period": 34},
    "QSTICK": {"period": 8},
    "VOLOSCILLATOR": {"short_period": 5, "long_period": 10},
}

SUBCHART_KEYS = {
    "RSI",
    "MACD_LINE",
    "MACD_SIGNAL",
    "MACD_HIST",
    "STOCH_K",
    "STOCH_D",
    "STOCHRSI_K",
    "STOCHRSI_D",
    "CCI",
    "WILLR",
    "ROC",
    "MFI",
    "ADX",
    "ATR",
    "STDDEV",
    "CMF",
    "BBP",
    "AO",
    "TSI",
    "QSTICK",
    "VOLOSC",
    "VOLOSCILLATOR",
    "HISTVOL",
    "VOLRANK",
}


def _default_pane(key: str) -> Literal["overlay", "subchart"]:
    """Infer chart pane from indicator key."""
    return "subchart" if key in SUBCHART_KEYS else "overlay"


def _merge_params(key: str, params: dict[str, Any]) -> dict[str, Any]:
    """Merge caller params over registry defaults."""
    merged = dict(INDICATOR_DEFAULTS.get(key, {}))
    merged.update(params)
    return merged


def max_warmup_bars(specs: list[IndicatorSpec], timeframe: str) -> int:
    """Return the largest warmup lookback required by a batch of indicator specs."""
    if not specs:
        return 0
    return max(
        warmup_bars(spec.key, _merge_params(spec.key.upper(), spec.params), timeframe=timeframe)
        for spec in specs
    )


def _series_value(value: Any) -> float | None:
    """Convert pandas scalar to JSON-safe float or null."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    return float(value)


class IndicatorService:
    """Compute indicators from OHLCV data."""

    def __init__(self, candle_service: CandleService | None = None) -> None:
        self._candle_service = candle_service or CandleService()

    def list_catalog(self) -> list[IndicatorCatalogEntry]:
        """Return all registry keys with metadata."""
        entries: list[IndicatorCatalogEntry] = []
        for key in sorted(INDICATORS):
            meta = INDICATOR_META.get(key, {})
            entries.append(
                IndicatorCatalogEntry(
                    key=key,
                    inputs=list(meta.get("inputs", ["close"])),
                    shared_params=list(meta.get("shared_params", ())),
                    default_params=dict(INDICATOR_DEFAULTS.get(key, {})),
                    pane=_default_pane(key),
                )
            )
        return entries

    def compute(
        self,
        conn: psycopg.Connection,
        symbol: str,
        timeframe: str,
        from_ts: int,
        to_ts: int,
        specs: list[IndicatorSpec],
    ) -> IndicatorComputeResponse:
        """
        Batch-compute indicators aligned to candle timestamps.

        Args:
            conn: Database connection.
            symbol: Trading pair.
            timeframe: Candle resolution.
            from_ts: Inclusive start unix seconds.
            to_ts: Inclusive end unix seconds.
            specs: Indicator specifications.

        Returns:
            Aligned indicator series.
        """
        if not specs:
            raise ValidationError("EMPTY_INDICATORS", "At least one indicator is required")

        warmup = max_warmup_bars(specs, timeframe)
        candles = self._candle_service.load_dataframe(
            conn,
            symbol,
            timeframe,
            from_ts,
            to_ts,
            warmup_bars=warmup,
        )
        series_list = self.compute_on_dataframe(
            candles,
            specs,
            output_from_ts=from_ts,
            output_to_ts=to_ts,
        )
        return IndicatorComputeResponse(
            symbol=symbol,
            timeframe=timeframe,
            series=series_list,
        )

    def compute_on_dataframe(
        self,
        candles: pd.DataFrame,
        specs: list[IndicatorSpec],
        prefix_end: int | None = None,
        output_from_ts: int | None = None,
        output_to_ts: int | None = None,
    ) -> list[IndicatorSeries]:
        """
        Compute indicators on an in-memory OHLCV frame.

        Args:
            candles: OHLCV DataFrame with ts column.
            specs: Indicator specifications.
            prefix_end: If set, only emit points through this inclusive bar index.
            output_from_ts: When set with ``output_to_ts``, only return points in
                this inclusive unix range (compute still uses the full frame).
            output_to_ts: Inclusive end of the visible output window.

        Returns:
            Indicator series aligned to candles (or prefix / visible window).
        """
        if candles.empty:
            return []

        compute_end = prefix_end if prefix_end is not None else len(candles) - 1
        frame = candles.iloc[: compute_end + 1]
        all_times = [_ts_to_unix(ts) for ts in frame["ts"]]

        output_start = 0
        output_end = len(all_times) - 1
        if output_from_ts is not None and output_to_ts is not None:
            window_start, window_end = frame_window_indices(all_times, output_from_ts, output_to_ts)
            if window_start < 0:
                return [
                    IndicatorSeries(
                        key=spec.key.upper(),
                        params=_merge_params(spec.key.upper(), spec.params),
                        pane=spec.pane or _default_pane(spec.key.upper()),
                        points=[],
                    )
                    for spec in specs
                ]
            output_start = window_start
            output_end = min(window_end, compute_end)

        times = all_times[output_start : output_end + 1]

        result: list[IndicatorSeries] = []
        for spec in specs:
            key = spec.key.upper()
            if key not in INDICATORS:
                raise ValidationError("INVALID_INDICATOR", f"Unknown indicator key: {spec.key}")

            params = _merge_params(key, spec.params)
            fn = INDICATORS[key]
            meta = INDICATOR_META.get(key, {})
            inputs = meta.get("inputs", ["close"])

            call_kwargs: dict[str, Any] = dict(params)
            for column in inputs:
                call_kwargs[column] = frame[column]

            try:
                values = fn(**call_kwargs)
            except TypeError as exc:
                raise ValidationError(
                    "INVALID_INDICATOR_PARAMS",
                    f"Invalid params for {key}: {exc}",
                ) from exc
            except ValueError:
                values = pd.Series([float("nan")] * len(frame))

            pane = spec.pane or _default_pane(key)
            sliced_values = values.iloc[output_start : output_end + 1]
            points = [
                IndicatorPoint(time=time, value=_series_value(val))
                for time, val in zip(times, sliced_values, strict=True)
            ]
            result.append(
                IndicatorSeries(key=key, params=params, pane=pane, points=points),
            )
        return result
