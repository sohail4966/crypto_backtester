"""Tests for WS ticket endpoint + service (BE-for-FE-L2-003)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.repositories.user_repository import UserRow
from api.services.ws_ticket_service import (
    WsTicketService,
    get_ws_ticket_service,
    reset_ws_ticket_service,
)


def _user() -> UserRow:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return UserRow(
        id=uuid4(),
        name="Ticket",
        email="ticket@example.com",
        password_hash="x",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def _reset_ws_ticket_singleton():
    reset_ws_ticket_service()
    yield
    reset_ws_ticket_service()


@patch("api.deps.connect")
@patch("api.deps.UserRepository.get_by_id")
def test_post_ws_tickets_requires_jwt_and_returns_ticket(
    mock_get: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """BE-for-FE-L2-003: JWT required; issues a single-use opaque ticket."""
    user = _user()
    mock_get.return_value = user
    mock_connect.return_value = MagicMock()

    unauth = client.post("/api/v1/ws/tickets")
    assert unauth.status_code == 401

    token = create_access_token(user_id=user.id, email=user.email)
    ok = client.post(
        "/api/v1/ws/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 201
    body = ok.json()
    assert isinstance(body["ticket"], str) and len(body["ticket"]) == 64
    assert body["expires_in"] >= 1

    consumed = get_ws_ticket_service().consume(body["ticket"])
    assert consumed == user.id
    # Single-use: second consume returns None.
    assert get_ws_ticket_service().consume(body["ticket"]) is None


def test_ws_ticket_service_expiry_returns_none() -> None:
    """Expired tickets must not authorise."""
    service = WsTicketService()
    user_id = uuid4()
    ticket, _ = service.issue(user_id, ttl_sec=0)
    # A 0-second TTL is already stale by the time we call consume.
    assert service.consume(ticket) is None


def test_ws_ticket_service_unknown_returns_none() -> None:
    service = WsTicketService()
    assert service.consume("not-a-ticket") is None
    assert service.consume("") is None
