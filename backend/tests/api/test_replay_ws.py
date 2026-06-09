"""
Tests for replay WebSocket.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from api.schemas.replay import ReplaySessionCreate
from api.services.replay_service import get_replay_service


@patch("api.services.replay_service.CandleService.load_dataframe")
def test_replay_websocket_step(mock_load: MagicMock, client: TestClient, sample_candles_df: pd.DataFrame) -> None:
    """WS step command emits candle and replay_state."""
    mock_load.return_value = sample_candles_df
    service = get_replay_service()
    session = service.create_session(
        MagicMock(),
        ReplaySessionCreate(
            symbol="BTC/USDT",
            timeframe="1d",
            start=1704067200,
            end=1706745600,
            step_timeframe="1d",
        ),
    )
    with client.websocket_connect(f"/ws/replay/{session.session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json({"action": "step", "count": 1})
        candle_msg = websocket.receive_json()
        assert candle_msg["type"] == "candle"
        indicators_msg = websocket.receive_json()
        assert indicators_msg["type"] == "indicators"
        state_msg = websocket.receive_json()
        assert state_msg["type"] == "replay_state"
        assert state_msg["bar_index"] == 0
