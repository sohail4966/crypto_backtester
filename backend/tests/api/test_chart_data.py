"""Tests for unified chart-data endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from api.repositories.symbol_repository import SymbolRow
from api.schemas.indicators import IndicatorComputeResponse, IndicatorPoint, IndicatorSeries


@patch("api.deps.connect")
@patch("api.services.chart_data_service.CandleService.get_candles")
@patch("api.services.chart_data_service.IndicatorService.compute")
def test_chart_data_bundles_candles_and_indicators(
    mock_compute: MagicMock,
    mock_candles: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """GET /chart-data returns candles and indicator map in one payload."""
    from api.schemas.candles import Bar, CandlesResponse

    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        mock_candles.return_value = CandlesResponse(
            symbol="BTC/USDT",
            timeframe="1h",
            bars=[
                Bar(time=1704067200, open=1, high=2, low=0.5, close=1.5, volume=10),
                Bar(time=1704070800, open=1.1, high=2.1, low=0.6, close=1.6, volume=11),
            ],
        )
        mock_compute.return_value = IndicatorComputeResponse(
            symbol="BTC/USDT",
            timeframe="1h",
            series=[
                IndicatorSeries(
                    key="EMA",
                    params={"period": 20},
                    pane="overlay",
                    points=[
                        IndicatorPoint(time=1704067200, value=1.4),
                        IndicatorPoint(time=1704070800, value=1.5),
                    ],
                )
            ],
        )

        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "BTC/USDT",
                "timeframe": "1h",
                "start": 1704067200,
                "end": 1704070800,
                "indicators": '[{"key":"EMA","params":{"period":20}}]',
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"]["id"] == "BTC/USDT"
    assert len(body["candles"]) == 2
    assert "EMA_20" in body["indicators"]
    assert body["signals"] == []
    assert body["trades"] == []


@patch("api.deps.connect")
@patch("api.services.chart_data_service.CandleService.get_candles")
def test_chart_data_unknown_symbol_returns_404(
    mock_candles: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """Missing symbol returns SYMBOL_NOT_FOUND."""
    mock_connect.return_value = MagicMock()
    with patch("api.repositories.symbol_repository.SymbolRepository.get_symbol", return_value=None):
        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "FOO/USDT",
                "timeframe": "1h",
                "start": 1704067200,
                "end": 1704070800,
            },
        )
    assert response.status_code == 404
    mock_candles.assert_not_called()


@patch("api.deps.connect")
@patch("api.services.chart_data_service.CandleService.get_latest_candles")
@patch("api.services.chart_data_service.CandleService.get_candles")
def test_chart_data_falls_back_to_latest_when_window_empty(
    mock_candles: MagicMock,
    mock_latest: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """Empty requested window loads the latest stored bars instead."""
    from api.schemas.candles import Bar, CandlesResponse

    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("SOL/USDT", "SOL", "USDT", True, 3, now)
    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        mock_candles.return_value = CandlesResponse(
            symbol="SOL/USDT",
            timeframe="1m",
            bars=[],
        )
        mock_latest.return_value = CandlesResponse(
            symbol="SOL/USDT",
            timeframe="1m",
            bars=[
                Bar(time=1700000000, open=1, high=2, low=0.5, close=1.5, volume=10),
            ],
        )

        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "SOL/USDT",
                "timeframe": "1m",
                "start": 2000000000,
                "end": 2000003600,
            },
        )

    assert response.status_code == 200
    assert len(response.json()["candles"]) == 1
    mock_latest.assert_called_once()
