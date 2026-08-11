"""Tests for screener HTTP API (Phase 8)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
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
    authed_client: TestClient,
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
                user_id=None,
                created_at=MagicMock(),
            ),
        ) as insert_mock,
    ):
        response = authed_client.post(
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
    assert insert_mock.call_args.kwargs["user_id"] is not None


@patch("api.services.scan_service.run_scan")
@patch("api.deps.connect")
def test_post_scan_no_persist(
    mock_connect: MagicMock,
    mock_run_scan: MagicMock,
    authed_client: TestClient,
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
        response = authed_client.post(
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
def test_post_scan_invalid_window(mock_connect: MagicMock, authed_client: TestClient) -> None:
    """start > end → 422."""
    mock_connect.return_value = MagicMock()
    response = authed_client.post(
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


@patch("api.services.scan_service.ScanRepository.get")
@patch("api.deps.connect")
def test_get_scan_ownership_mismatch_404(
    mock_connect: MagicMock,
    mock_get: MagicMock,
    authed_client: TestClient,
) -> None:
    """GET /scan/{id} for another user's run → SCAN_NOT_FOUND (G-004)."""
    from datetime import UTC, datetime

    mock_connect.return_value = MagicMock()
    scan_id = uuid4()
    mock_get.return_value = ScanRunRow(
        scan_id=scan_id,
        timeframes=["1d"],
        symbols=["BTC/USDT"],
        start_ts=1704067200,
        end_ts=1706745600,
        condition_config=CONDITION,
        alert_trigger="edge",
        matches=[],
        alert_count=0,
        duration_ms=1,
        status="completed",
        error_message=None,
        user_id=uuid4(),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    response = authed_client.get(f"/api/v1/scan/{scan_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"


@patch("api.services.scan_service.ScanRepository.get")
@patch("api.deps.connect")
def test_get_scan_owner_ok(
    mock_connect: MagicMock,
    mock_get: MagicMock,
    authed_client: TestClient,
    auth_user,
) -> None:
    """Owner can retrieve their persisted scan (G-004 / G-012)."""
    from datetime import UTC, datetime

    mock_connect.return_value = MagicMock()
    scan_id = uuid4()
    mock_get.return_value = ScanRunRow(
        scan_id=scan_id,
        timeframes=["1d"],
        symbols=["BTC/USDT"],
        start_ts=1704067200,
        end_ts=1706745600,
        condition_config=CONDITION,
        alert_trigger="edge",
        matches=[],
        alert_count=0,
        duration_ms=1,
        status="completed",
        error_message=None,
        user_id=auth_user.id,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    response = authed_client.get(f"/api/v1/scan/{scan_id}")
    assert response.status_code == 200
    assert response.json()["scan_id"] == str(scan_id)


def test_scan_repository_insert_commits() -> None:
    """ScanRepository.insert commits on the request connection (BE-001 / G-012)."""
    from datetime import UTC, datetime

    from api.repositories.scan_repository import ScanRepository

    conn = MagicMock()
    cursor = MagicMock()
    scan_id = uuid4()
    cursor.fetchone.return_value = (
        scan_id,
        ["1d"],
        ["BTC/USDT"],
        1704067200,
        1706745600,
        CONDITION,
        "edge",
        [],
        0,
        1,
        "completed",
        None,
        uuid4(),
        datetime(2024, 1, 1, tzinfo=UTC),
    )
    conn.cursor.return_value.__enter__.return_value = cursor

    ScanRepository().insert(
        conn,
        scan_id=scan_id,
        timeframes=["1d"],
        symbols=["BTC/USDT"],
        start_ts=1704067200,
        end_ts=1706745600,
        condition_config=CONDITION,
        alert_trigger="edge",
        matches=[],
        alert_count=0,
        duration_ms=1,
        user_id=uuid4(),
    )
    conn.commit.assert_called_once()


def test_passwordless_user_create_hard_fails() -> None:
    """G-011: UserRepository.create must not insert null-hash users."""
    from api.repositories.user_repository import UserRepository

    with pytest.raises(RuntimeError, match="Passwordless"):
        UserRepository().create(MagicMock(), "A", "a@example.com")

