"""
Tests for in-memory replay service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from api.schemas.indicators import IndicatorSpec
from api.schemas.replay import ReplaySessionCreate
from api.services.replay_service import ReplayService


@patch("api.services.replay_service.CandleService.load_dataframe")
def test_replay_step_emits_prefix_indicators(mock_load: MagicMock, sample_candles_df: pd.DataFrame) -> None:
    """Indicators at step N only use bars 0..N."""
    mock_load.return_value = sample_candles_df
    service = ReplayService()
    conn = MagicMock()
    session = service.create_session(
        conn,
        ReplaySessionCreate(
            symbol="BTC/USDT",
            timeframe="1d",
            start=1704067200,
            end=1706745600,
            indicators=[IndicatorSpec(key="SMA", params={"period": 2})],
            step_timeframe="1d",
        ),
    )
    bar1, ind1, done1 = service.step(session)
    assert bar1 is not None
    assert done1 is False
    assert len(ind1[0].points) == 1

    bar2, ind2, _ = service.step(session)
    assert bar2 is not None
    assert len(ind2[0].points) == 2


@patch("api.services.replay_service.CandleService.load_dataframe")
def test_replay_seek_out_of_range(mock_load: MagicMock, sample_candles_df: pd.DataFrame) -> None:
    """Seek before window raises validation error."""
    mock_load.return_value = sample_candles_df
    service = ReplayService()
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
    import pytest

    from api.exceptions import ValidationError

    with pytest.raises(ValidationError):
        service.seek(session, 1)
