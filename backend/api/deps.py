"""
FastAPI dependencies shared across routers.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import psycopg
from fastapi import Depends, Header, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api import rate_limiter, settings
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
    A missing or invalid token returns ``None`` — callers that need fail-closed
    behaviour (e.g. run-scoped overlays) MUST enforce the check explicitly
    (BE-L2-007).
    """
    token = _extract_bearer_token(credentials, authorization)
    if not token:
        return None
    try:
        return _user_from_token(conn, token)
    except UnauthorizedError:
        return None


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
    """Per-user AI RPM limiter delegated to the shared façade (BE-L2-009)."""
    rate_limiter.check_ai_rpm(current.id)


def acquire_ws_slot(user_id: UUID) -> None:
    """Reserve a WS connection slot for a user or raise (BE-L2-009)."""
    rate_limiter.acquire_ws(user_id)


def release_ws_slot(user_id: UUID) -> None:
    """Release a previously acquired WS slot (BE-L2-009)."""
    rate_limiter.release_ws(user_id)


def _client_ip(request: Request) -> str:
    """
    Return best-effort client IP, honouring proxy headers only when trusted
    (BE-L2-010). Reject spoofed ``X-Forwarded-For`` values by default.
    """
    if settings.trust_proxy_headers():
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_anonymous_ip(request: Request) -> None:
    """
    Per-IP anonymous limiter — runs BEFORE Pydantic body validation so a caller
    hammering ``POST /auth/register`` with malformed payloads still gets throttled
    (BE-L2-010). The per-email portion of the limiter is enforced inside the
    router after the body has been parsed (see ``AuthService.register_with_limits``).
    """
    ip_limit = settings.auth_register_ip_rpm()
    try:
        rate_limiter.get_rate_limiter().check_rpm(
            "register:ip",
            _client_ip(request),
            limit=ip_limit,
            window_sec=60,
        )
    except rate_limiter.RateLimitDeniedError as exc:
        from api.exceptions import RateLimitError

        raise RateLimitError(
            "RATE_LIMITED", f"Too many registration attempts (per-IP): {exc.message}"
        ) from exc


def rate_limit_register_email(email: str) -> None:
    """
    Enforce the per-email portion of the anonymous-register limiter (BE-L2-010).
    Called from routers after Pydantic validation extracts the email.
    """
    email_limit = settings.auth_register_email_rph()
    try:
        rate_limiter.get_rate_limiter().check_rpm(
            "register:email",
            email.strip().lower(),
            limit=email_limit,
            window_sec=3600,
        )
    except rate_limiter.RateLimitDeniedError as exc:
        from api.exceptions import RateLimitError

        raise RateLimitError(
            "RATE_LIMITED", f"Too many registration attempts (per-email): {exc.message}"
        ) from exc


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


def resolve_ws_user(
    websocket: WebSocket,
    token: str | None = None,
    ticket: str | None = None,
) -> UserRow:
    """
    Resolve the WebSocket subject (BE-for-FE-L2-003).

    Consumes a one-shot ticket first (preferred), then falls back to
    ``?token=`` / ``Authorization: Bearer`` for backwards compatibility.
    Raises ``UnauthorizedError`` when no credentials are available or the
    supplied credentials are invalid / expired / already used.
    """
    if ticket:
        from api.services.ws_ticket_service import get_ws_ticket_service

        user_id = get_ws_ticket_service().consume(ticket)
        if user_id is None:
            raise UnauthorizedError("INVALID_TICKET", "Ticket missing or already used")
        conn = connect()
        try:
            user = _users.get_by_id(conn, user_id)
        finally:
            conn.close()
        if user is None:
            raise UnauthorizedError("USER_NOT_FOUND", "Ticket subject unknown")
        return user

    raw = resolve_ws_token(websocket, token)
    if not raw:
        raise UnauthorizedError()
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "ws_bearer_in_url",
        extra={"ws_path": websocket.url.path if hasattr(websocket, "url") else ""},
    )
    return user_from_ws_token(raw)
