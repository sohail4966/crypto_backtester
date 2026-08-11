"""Tests for JWT auth (Phase 11) and hardening (BE-002/016/024)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from api.auth import create_access_token, hash_password, verify_password
from api.repositories.user_repository import UserRow
from api.repositories.watchlist_repository import WatchlistRow


def _user(
    *,
    password_hash: str | None = None,
    email: str = "a@example.com",
) -> UserRow:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return UserRow(
        id=uuid4(),
        name="Alice",
        email=email,
        password_hash=password_hash,
        created_at=now,
        updated_at=now,
    )


def test_hash_and_verify_password_roundtrip() -> None:
    digest = hash_password("secret-pass")
    assert verify_password("secret-pass", digest)
    assert not verify_password("wrong", digest)
    assert not verify_password("secret-pass", None)


@patch("api.deps.connect")
@patch("api.services.auth_service.SymbolService.list_symbols", return_value=[])
@patch("api.services.auth_service.WatchlistRepository.create")
@patch("api.services.auth_service.WatchlistRepository.set_symbols")
@patch("api.services.auth_service.UserRepository.create_with_password")
def test_register_returns_jwt(
    mock_create: MagicMock,
    _mock_set_symbols: MagicMock,
    mock_wl_create: MagicMock,
    _mock_symbols: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    user = _user(password_hash="x")
    mock_create.return_value = user
    mock_wl_create.return_value = WatchlistRow(
        id=uuid4(),
        user_id=user.id,
        name="Default",
        is_default=True,
        sort_order=0,
        created_at=user.created_at,
    )
    conn = MagicMock()
    mock_connect.return_value = conn

    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "a@example.com", "password": "secret-pass"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user_id"] == str(user.id)
    conn.commit.assert_called()


@patch("api.deps.connect")
@patch("api.services.auth_service.UserRepository.get_by_email")
def test_login_ok_and_bad_password(
    mock_get: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    digest = hash_password("secret-pass")
    user = _user(password_hash=digest)
    mock_get.return_value = user
    mock_connect.return_value = MagicMock()

    ok = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "secret-pass"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "nope"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_claim_endpoint_removed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/claim",
        json={"email": "a@example.com", "password": "secret-pass"},
    )
    assert response.status_code == 404


@patch("api.deps.connect")
@patch("api.deps.UserRepository.get_by_id")
def test_auth_me_requires_jwt(
    mock_get_user: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    user = _user(password_hash="x")
    mock_get_user.return_value = user
    mock_connect.return_value = MagicMock()

    unauth = client.get("/api/v1/auth/me")
    assert unauth.status_code == 401

    token = create_access_token(user_id=user.id, email=user.email)
    ok = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200
    assert ok.json()["email"] == user.email
    assert "password_hash" not in ok.json()


@patch("api.deps.connect")
@patch("api.deps.UserRepository.get_by_id")
@patch("api.services.watchlist_service.WatchlistService.list_watchlists", return_value=[])
def test_watchlist_requires_matching_jwt(
    _mock_list: MagicMock,
    mock_get_user: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    owner = _user()
    other = _user(email="b@example.com")
    mock_get_user.return_value = owner
    mock_connect.return_value = MagicMock()

    unauth = client.get(f"/api/v1/users/{owner.id}/watchlists")
    assert unauth.status_code == 401

    token = create_access_token(user_id=owner.id, email=owner.email)
    ok = client.get(
        f"/api/v1/users/{owner.id}/watchlists",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200

    mock_get_user.return_value = other
    other_token = create_access_token(user_id=other.id, email=other.email)
    forbidden = client.get(
        f"/api/v1/users/{owner.id}/watchlists",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden.status_code == 403


@patch("api.deps.connect")
@patch("api.services.auth_service.UserRepository.create_with_password")
def test_register_duplicate_email_uniform_code(
    mock_create: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """Register conflict uses REGISTRATION_FAILED, not EMAIL_EXISTS (G-008)."""
    import psycopg

    conn = MagicMock()
    mock_connect.return_value = conn
    mock_create.side_effect = psycopg.errors.UniqueViolation("users_email")

    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "a@example.com", "password": "secret-pass"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REGISTRATION_FAILED"
    assert "EMAIL_EXISTS" not in response.text


@patch("api.deps.connect")
@patch("api.services.auth_service.UserRepository.get_by_email")
def test_login_unknown_email_still_runs_bcrypt(
    mock_get: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """BE-L2-011: unknown-email login path still exercises bcrypt.checkpw."""
    mock_connect.return_value = MagicMock()
    mock_get.return_value = None

    with patch("api.auth.bcrypt.checkpw", return_value=False) as mock_checkpw:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "does-not-matter"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert mock_checkpw.called, "unknown email path must still call bcrypt.checkpw"


@patch("api.deps.connect")
@patch("api.services.auth_service.UserRepository.create_with_password")
def test_register_provisioning_conflict_maps_to_distinct_code(
    mock_create: MagicMock,
    mock_connect: MagicMock,
    client: TestClient,
) -> None:
    """BE-L2-008: non-email unique violations surface as PROVISIONING_CONFLICT."""
    import psycopg

    conn = MagicMock()
    mock_connect.return_value = conn

    exc = psycopg.errors.UniqueViolation("watchlist default clash")
    mock_create.side_effect = exc

    with patch(
        "api.services.auth_service._extract_constraint_name",
        return_value="watchlists_user_default_key",
    ):
        response = client.post(
            "/api/v1/auth/register",
            json={"name": "Bob", "email": "b@example.com", "password": "secret-pass"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROVISIONING_CONFLICT"


def test_post_users_returns_410_gone(client: TestClient) -> None:
    """BE-L2-019: POST /users is retired in favour of /auth/register."""
    response = client.post(
        "/api/v1/users",
        json={"name": "Alice", "email": "a@example.com"},
    )
    assert response.status_code == 410
    body = response.json()
    assert body["error"]["code"] == "GONE"


@patch("api.deps.connect")
def test_health_stays_public(mock_connect: MagicMock, client: TestClient) -> None:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn
    response = client.get("/api/v1/meta/health")
    assert response.status_code == 200
