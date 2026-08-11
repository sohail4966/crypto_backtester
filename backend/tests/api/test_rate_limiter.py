"""Tests for the rate-limiter façade (BE-L2-009, BE-L2-010)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.rate_limiter import (
    InProcessRateLimiter,
    RateLimitDeniedError,
    reset_rate_limiter,
)


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_rate_limiter()
    yield
    reset_rate_limiter()


def test_in_process_rpm_denies_over_limit() -> None:
    limiter = InProcessRateLimiter()
    for _ in range(3):
        limiter.check_rpm("ns", "k", limit=3, window_sec=60)
    with pytest.raises(RateLimitDeniedError):
        limiter.check_rpm("ns", "k", limit=3, window_sec=60)


def test_in_process_slot_acquire_release_symmetric() -> None:
    limiter = InProcessRateLimiter()
    limiter.acquire_slot("ws", "user", max_slots=1)
    assert limiter.slot_count("ws", "user") == 1
    with pytest.raises(RateLimitDeniedError):
        limiter.acquire_slot("ws", "user", max_slots=1)
    limiter.release_slot("ws", "user")
    assert limiter.slot_count("ws", "user") == 0
    limiter.release_slot("ws", "user")
    assert limiter.slot_count("ws", "user") == 0


@patch("api.settings.auth_register_ip_rpm", return_value=2)
@patch("api.settings.auth_register_email_rph", return_value=1000)
@patch("api.deps.connect")
@patch("api.services.auth_service.UserRepository.create_with_password")
def test_register_ip_rate_limit_returns_429(
    mock_create: MagicMock,
    mock_connect: MagicMock,
    _mock_email_limit: MagicMock,
    _mock_ip_limit: MagicMock,
    client: TestClient,
) -> None:
    """BE-L2-010: repeated register calls from the same IP get 429."""
    from api.repositories.user_repository import UserRow
    from datetime import UTC, datetime

    now = datetime(2024, 1, 1, tzinfo=UTC)
    mock_create.return_value = UserRow(
        id=uuid4(),
        name="Alice",
        email="a@example.com",
        password_hash="x",
        created_at=now,
        updated_at=now,
    )
    mock_connect.return_value = MagicMock()

    with (
        patch("api.services.auth_service.WatchlistRepository.create") as mock_wl,
        patch("api.services.auth_service.WatchlistRepository.set_symbols"),
        patch("api.services.auth_service.SymbolService.list_symbols", return_value=[]),
    ):
        from api.repositories.watchlist_repository import WatchlistRow

        mock_wl.return_value = WatchlistRow(
            id=uuid4(),
            user_id=uuid4(),
            name="Default",
            is_default=True,
            sort_order=0,
            created_at=now,
        )
        r1 = client.post(
            "/api/v1/auth/register",
            json={"name": "A", "email": "one@example.com", "password": "strong-pw"},
        )
        r2 = client.post(
            "/api/v1/auth/register",
            json={"name": "B", "email": "two@example.com", "password": "strong-pw"},
        )
        r3 = client.post(
            "/api/v1/auth/register",
            json={"name": "C", "email": "three@example.com", "password": "strong-pw"},
        )

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r3.status_code == 429
    assert r3.json()["error"]["code"] == "RATE_LIMITED"
