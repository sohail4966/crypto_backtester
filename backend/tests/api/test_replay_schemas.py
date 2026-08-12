"""Schema-level tests for replay REST bodies (BE-L2-006)."""

from __future__ import annotations

from api.schemas.replay import ReplaySessionCreate


def test_replay_session_create_accepts_optional_user_id() -> None:
    """user_id is optional metadata, not an ownership credential."""
    body = ReplaySessionCreate(
        symbol="BTC/USDT",
        timeframe="1d",
        start=1704067200,
        user_id="00000000-0000-0000-0000-000000000001",
    )
    assert str(body.user_id) == "00000000-0000-0000-0000-000000000001"


def test_replay_session_create_accepts_normal_fields() -> None:
    body = ReplaySessionCreate(
        symbol="BTC/USDT",
        timeframe="1d",
        start=1704067200,
    )
    assert body.symbol == "BTC/USDT"
    assert body.autoplay is False
