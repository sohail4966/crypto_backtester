"""Tests for Phase 4b REST replay chunks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient


@patch("api.services.replay_service.CandleService.load_dataframe")
def test_replay_run_chunk_sequence(mock_load: MagicMock, client: TestClient, sample_candles_df: pd.DataFrame) -> None:
    """Create run then fetch sequential chunks."""
    mock_load.return_value = sample_candles_df
    conn = MagicMock()

    with patch("api.deps.connect", return_value=conn):
        with patch(
            "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        ) as mock_get_symbol:
            from datetime import UTC, datetime

            from api.repositories.symbol_repository import SymbolRow

            mock_get_symbol.return_value = SymbolRow(
                "BTC/USDT", "BTC", "USDT", True, 1, datetime(2024, 1, 1, tzinfo=UTC)
            )

            create = client.post(
                "/api/v1/replay/runs",
                json={
                    "symbolId": "BTC/USDT",
                    "timeframe": "1d",
                    "start": 1704067200,
                    "end": 1706745600,
                    "indicators": [{"key": "SMA", "params": {"period": 2}}],
                },
            )
            assert create.status_code == 201
            run_id = create.json()["runId"]
            assert create.json()["totalBars"] == 5

            first_ts = int(sample_candles_df["ts"].iloc[0].timestamp())
            chunk1 = client.get(
                f"/api/v1/replay/{run_id}/chunk",
                params={"from": first_ts, "limit": 2},
            )
            assert chunk1.status_code == 200
            assert len(chunk1.json()["candles"]) == 2

            next_from = chunk1.json()["candles"][-1]["time"] + 86400
            chunk2 = client.get(
                f"/api/v1/replay/{run_id}/chunk",
                params={"from": next_from, "limit": 2},
            )
            assert chunk2.status_code == 200
            assert len(chunk2.json()["candles"]) >= 1

            trades = client.get(f"/api/v1/replay/{run_id}/trades")
            assert trades.status_code == 200
            assert trades.json()["trades"] == []

            deleted = client.delete(f"/api/v1/replay/{run_id}")
            assert deleted.status_code == 204


@patch("api.services.replay_service.CandleService.load_dataframe")
def test_replay_chunk_unknown_run_returns_404(mock_load: MagicMock, client: TestClient) -> None:
    """Chunk fetch for missing run returns 404."""
    _ = mock_load
    response = client.get(
        "/api/v1/replay/00000000-0000-0000-0000-000000000099/chunk",
        params={"from": 1704067200},
    )
    assert response.status_code == 404
