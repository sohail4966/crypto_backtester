"""
Tests for historical candle service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from api.exceptions import ValidationError
from api.services.candle_service import CandleService
from tests.api.conftest import make_symbol_response


@patch("api.services.candle_service.get_candles")
@patch("api.services.candle_service.SymbolService.require_active_symbol")
def test_candle_default_limit(mock_require: MagicMock, mock_get: MagicMock) -> None:
    """Default limit is 1000 when not specified."""
    mock_require.return_value = make_symbol_response()
    ts = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    mock_get.return_value = pd.DataFrame(
        {
            "ts": ts,
            "open": [1.0] * 5,
            "high": [2.0] * 5,
            "low": [0.5] * 5,
            "close": [1.5] * 5,
            "volume": [100.0] * 5,
        }
    )
    service = CandleService()
    result = service.get_candles(MagicMock(), "BTC/USDT", "1d", 1704067200, 1706745600)
    assert len(result.bars) == 5
    assert result.bars[0].time == int(ts[0].timestamp())


@patch("api.services.candle_service.get_candles")
@patch("api.services.candle_service.SymbolService.require_active_symbol")
def test_candle_limit_exceeded_raises(mock_require: MagicMock, mock_get: MagicMock) -> None:
    """Limit above max raises validation error."""
    mock_require.return_value = make_symbol_response()
    service = CandleService()
    with pytest.raises(ValidationError):
        service.get_candles(
            MagicMock(),
            "BTC/USDT",
            "1d",
            1704067200,
            1706745600,
            limit=9999,
        )
