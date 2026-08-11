"""Schema-level tests for replay REST bodies (BE-L2-006)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas.replay import ReplaySessionCreate


def test_replay_session_create_rejects_user_id_field() -> None:
    """BE-L2-006: clients can no longer forge ownership by sending user_id."""
    with pytest.raises(ValidationError) as exc_info:
        ReplaySessionCreate(  # type: ignore[call-arg]
            symbol="BTC/USDT",
            timeframe="1d",
            start=1704067200,
            user_id="00000000-0000-0000-0000-000000000001",
        )
    assert "extra" in str(exc_info.value).lower() or "forbid" in str(exc_info.value).lower()


def test_replay_session_create_accepts_normal_fields() -> None:
    body = ReplaySessionCreate(
        symbol="BTC/USDT",
        timeframe="1d",
        start=1704067200,
    )
    assert body.symbol == "BTC/USDT"
    assert body.autoplay is False
