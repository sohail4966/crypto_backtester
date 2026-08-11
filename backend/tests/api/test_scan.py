"""Tests for screener HTTP API (Phase 8)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from api.repositories.scan_repository import ScanRunRow
from api.repositories.symbol_repository import SymbolRow
from screener.types import ScanMatch, ScanResult


def _sample_candles() -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
    close = pd.Series([100.0] * 30)
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * 30,
        }
    )


CONDITION = {"indicator": "RSI", "params": {"period": 2}, "op": "<", "value": 100}


@patch("api.services.scan_service.get_candles")
@patch("api.deps.connect")
def test_post_scan_persists(
    mock_connect: MagicMock,
    mock_get_candles: MagicMock,
    client: TestClient,
) -> None:
    """POST /scan runs and persists when persist=true."""
    conn = MagicMock()
    mock_connect.return_value = conn
    mock_get_candles.return_value = _sample_candles()

    symbol_row = SymbolRow(
        symbol="BTC/USDT",
        base="BTC",
        quote="USDT",
        is_active=True,
        sort_order=1,
        created_at=None,
        exchange="binance",
        tick_size=0.01,
        lot_size=0.001,
        asset_type="spot",
    )

    scan_id = uuid4()
    with (
        patch(
            "api.services.scan_service.SymbolRepository.list_symbols",
            return_value=[symbol_row],
        ),
        patch(
            "api.services.scan_service.ScanRepository.insert",
            return_value=ScanRunRow(
                scan_id=scan_id,
                timeframes=["1h", "1d"],
                symbols=["BTC/USDT"],
                start_ts=1704067200,
                end_ts=1706745600,
                condition_config=CONDITION,
                alert_trigger="level",
                matches=[],
                alert_count=2,
                duration_ms=5,
                status="completed",
                error_message=None,
                created_at=MagicMock(),
            ),
        ) as insert_mock,
    ):
        response = client.post(
            "/api/v1/scan",
            json={
                "timeframes": ["1h", "1d"],
                "start": 1704067200,
                "end": 1706745600,
                "condition": CONDITION,
                "alert_trigger": "level",
                "persist": True,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["persisted"] is True
    assert body["scan_id"] is not None
    assert body["scanned_pairs"] == 2
    assert body["alert_count"] >= 1
    insert_mock.assert_called_once()


@patch("api.services.scan_service.run_scan")
@patch("api.deps.connect")
def test_post_scan_no_persist(
    mock_connect: MagicMock,
    mock_run_scan: MagicMock,
    client: TestClient,
) -> None:
    """persist=false skips repository insert."""
    mock_connect.return_value = MagicMock()
    mock_run_scan.return_value = ScanResult(
        matches=[
            ScanMatch(
                symbol="ETH/USDT",
                timeframe="1d",
                bar_ts="2024-01-30T00:00:00+00:00",
                triggered=True,
                close=100.0,
            )
        ],
        alert_count=1,
        duration_ms=3,
        scanned_pairs=1,
        condition=CONDITION,
        alert_trigger="edge",
        errors=[],
    )

    with patch(
        "api.services.scan_service.ScanRepository.insert"
    ) as insert_mock:
        response = client.post(
            "/api/v1/scan",
            json={
                "timeframes": ["1d"],
                "start": 1704067200,
                "end": 1706745600,
                "symbols": ["ETH/USDT"],
                "condition": CONDITION,
                "persist": False,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["persisted"] is False
    assert body["scan_id"] is None
    assert body["alert_count"] == 1
    insert_mock.assert_not_called()


@patch("api.deps.connect")
def test_post_scan_invalid_window(mock_connect: MagicMock, client: TestClient) -> None:
    """start > end → 422."""
    mock_connect.return_value = MagicMock()
    response = client.post(
        "/api/v1/scan",
        json={
            "timeframes": ["1d"],
            "start": 1706745600,
            "end": 1704067200,
            "symbols": ["BTC/USDT"],
            "condition": CONDITION,
        },
    )
    assert response.status_code == 422
