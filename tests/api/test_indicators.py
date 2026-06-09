"""
Tests for indicator catalog and compute.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.exceptions import ValidationError
from api.schemas.indicators import IndicatorSpec
from api.services.indicator_service import IndicatorService
from indicators.registry import INDICATORS


def test_catalog_lists_all_registry_keys() -> None:
    """Catalog contains every registry key."""
    service = IndicatorService()
    keys = {entry.key for entry in service.list_catalog()}
    assert keys == set(INDICATORS.keys())


def test_compute_rsi_on_dataframe(sample_candles_df: pd.DataFrame) -> None:
    """RSI compute returns aligned points with warmup nulls."""
    service = IndicatorService()
    specs = [IndicatorSpec(key="RSI", params={"period": 3})]
    series = service.compute_on_dataframe(sample_candles_df, specs)
    assert len(series) == 1
    assert series[0].key == "RSI"
    assert len(series[0].points) == len(sample_candles_df)
    assert series[0].points[0].value is None


def test_compute_rsi_with_warmup_history_seeds_window_start() -> None:
    """Pre-window candles seed RSI so the first visible bar is not null."""
    service = IndicatorService()
    ts = pd.to_datetime(
        [f"2024-12-{day:02d}" for day in range(28, 32)]
        + [f"2025-01-{day:02d}" for day in range(1, 6)],
        utc=True,
    )
    close = pd.Series(
        [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
        dtype=float,
    )
    frame = pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 1,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * len(close),
        }
    )
    from_ts = int(ts[4].timestamp())
    to_ts = int(ts[-1].timestamp())
    specs = [IndicatorSpec(key="RSI", params={"period": 3})]
    series = service.compute_on_dataframe(
        frame,
        specs,
        output_from_ts=from_ts,
        output_to_ts=to_ts,
    )
    assert len(series[0].points) == 5
    assert series[0].points[0].value is not None


@patch("api.services.indicator_service.CandleService.load_dataframe")
def test_compute_loads_warmup_candles(mock_load: MagicMock, sample_candles_df: pd.DataFrame) -> None:
    """Indicator compute requests extra pre-window bars for seeding."""
    mock_load.return_value = sample_candles_df
    service = IndicatorService()
    conn = MagicMock()
    specs = [IndicatorSpec(key="RSI", params={"period": 14})]
    service.compute(conn, "BTC/USDT", "1d", 1704067200, 1706745600, specs)
    mock_load.assert_called_once()
    assert mock_load.call_args.kwargs["warmup_bars"] == 140


def test_compute_unknown_indicator_raises() -> None:
    """Unknown key raises validation error."""
    service = IndicatorService()
    with pytest.raises(ValidationError):
        service.compute_on_dataframe(
            pd.DataFrame(
                {
                    "ts": pd.to_datetime(["2024-01-01"], utc=True),
                    "open": [1.0],
                    "high": [2.0],
                    "low": [0.5],
                    "close": [1.5],
                    "volume": [10.0],
                }
            ),
            [IndicatorSpec(key="NOT_REAL")],
        )


@patch("api.routers.indicators._service.compute")
def test_compute_endpoint(mock_compute: MagicMock, client: TestClient) -> None:
    """POST /indicators/compute delegates to service."""
    from api.schemas.indicators import IndicatorComputeResponse, IndicatorSeries

    mock_compute.return_value = IndicatorComputeResponse(
        symbol="BTC/USDT",
        timeframe="1d",
        series=[
            IndicatorSeries(key="RSI", params={"period": 14}, pane="subchart", points=[]),
        ],
    )
    response = client.post(
        "/api/v1/indicators/compute",
        json={
            "symbol": "BTC/USDT",
            "timeframe": "1d",
            "from": 1704067200,
            "to": 1706745600,
            "indicators": [{"key": "RSI", "params": {"period": 14}}],
        },
    )
    assert response.status_code == 200
    assert response.json()["symbol"] == "BTC/USDT"
