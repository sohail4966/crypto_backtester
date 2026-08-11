"""
FastAPI dependencies shared across routers.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Generator
from threading import Lock
from uuid import UUID

import psycopg
from fastapi import Depends, Header, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api import settings
from api.auth import ForbiddenError, UnauthorizedError, decode_access_token
from api.exceptions import ValidationError
from api.repositories.user_repository import UserRepository, UserRow
from data.db import connect

_bearer = HTTPBearer(auto_error=False)
_users = UserRepository()

# In-process AI rate limiter: user_id -> deque of request timestamps (BE-004).
_ai_hits: dict[UUID, deque[float]] = defaultdict(deque)
_ai_lock = Lock()

# In-process WS connection counts per user (BE-004).
_ws_counts: dict[UUID, int] = defaultdict(int)
_ws_lock = Lock()


def get_db() -> Generator[psycopg.Connection, None, None]:
    """
    Yield a database connection for the request lifecycle.

    Yields:
        Open psycopg connection closed after the request.
    """
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    authorization: str | None,
) -> str | None:
    """Pull a Bearer token from HTTPBearer or raw Authorization header."""
    if credentials is not None:
        return credentials.credentials
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def get_current_user(
    conn: psycopg.Connection = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    authorization: str | None = Header(default=None),
) -> UserRow:
    """
    Require a valid Bearer JWT and load the subject user.

    Raises:
        UnauthorizedError: Missing/invalid token or unknown subject.
    """
    token = _extract_bearer_token(credentials, authorization)
    if not token:
        raise UnauthorizedError()

    return _user_from_token(conn, token)


def get_optional_user(
    conn: psycopg.Connection = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    authorization: str | None = Header(default=None),
) -> UserRow | None:
    """
    Load the subject user when a Bearer token is present; otherwise ``None``.

    Used by chart-data: public candle windows, auth required when ``runId`` is set.
    """
    token = _extract_bearer_token(credentials, authorization)
    if not token:
        return None
    return _user_from_token(conn, token)


def _user_from_token(conn: psycopg.Connection, token: str) -> UserRow:
    """Decode JWT and load the subject user."""
    claims = decode_access_token(token)
    sub = claims.get("sub")
    if not sub:
        raise UnauthorizedError("INVALID_TOKEN", "Token missing subject")
    try:
        user_id = UUID(str(sub))
    except ValueError as exc:
        raise UnauthorizedError("INVALID_TOKEN", "Token subject is not a UUID") from exc

    user = _users.get_by_id(conn, user_id)
    if user is None:
        raise UnauthorizedError("USER_NOT_FOUND", "Token subject unknown")
    return user


def require_same_user(path_user_id: UUID, current: UserRow) -> None:
    """
    Enforce JWT subject matches the path user id.

    Raises:
        ForbiddenError: When ids differ.
    """
    if current.id != path_user_id:
        raise ForbiddenError("FORBIDDEN", "Cannot access another user's resources")


def rate_limit_ai(current: UserRow = Depends(get_current_user)) -> None:
    """Simple in-process per-user AI RPM limiter (BE-004)."""
    limit = settings.ai_max_rpm()
    now = time.monotonic()
    window = 60.0
    with _ai_lock:
        hits = _ai_hits[current.id]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            raise ValidationError(
                "RATE_LIMITED",
                f"AI rate limit exceeded ({limit} requests per minute)",
            )
        hits.append(now)


def acquire_ws_slot(user_id: UUID) -> None:
    """Reserve a WS connection slot for a user or raise."""
    max_conn = settings.ws_max_connections_per_user()
    with _ws_lock:
        if _ws_counts[user_id] >= max_conn:
            raise ValidationError(
                "WS_LIMIT",
                f"Max {max_conn} concurrent WebSocket connections per user",
            )
        _ws_counts[user_id] += 1


def release_ws_slot(user_id: UUID) -> None:
    """Release a previously acquired WS slot."""
    with _ws_lock:
        if _ws_counts[user_id] > 0:
            _ws_counts[user_id] -= 1


def resolve_ws_token(websocket: WebSocket, token: str | None = None) -> str | None:
    """Extract Bearer token from query ``token`` or Authorization header."""
    if token:
        return token
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def user_from_ws_token(token: str) -> UserRow:
    """Load user for a WS token (opens a short-lived DB connection)."""
    conn = connect()
    try:
        return _user_from_token(conn, token)
    finally:
        conn.close()
