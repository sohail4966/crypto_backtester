"""
FastAPI dependencies shared across routers.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import psycopg
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import ForbiddenError, UnauthorizedError, decode_access_token
from api.repositories.user_repository import UserRepository, UserRow
from data.db import connect

_bearer = HTTPBearer(auto_error=False)
_users = UserRepository()


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
    token: str | None = None
    if credentials is not None:
        token = credentials.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise UnauthorizedError()

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
