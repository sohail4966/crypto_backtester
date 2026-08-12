"""
FastAPI dependencies shared across routers.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import psycopg
from fastapi import Request, WebSocket

from api import rate_limiter
from data.db import connect


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


def _client_ip(request: Request) -> str:
    """Best-effort client IP (no proxy trust by default)."""
    return request.client.host if request.client else "unknown"


def rate_limit_ai(request: Request) -> None:
    """Per-IP AI RPM limiter (no AuthN)."""
    rate_limiter.check_ai_rpm(_client_ip(request))


def acquire_ws_slot(key: UUID | str) -> None:
    """Reserve a WS connection slot for a connection key or raise."""
    rate_limiter.acquire_ws(key)


def release_ws_slot(key: UUID | str) -> None:
    """Release a previously acquired WS slot."""
    rate_limiter.release_ws(key)


def ws_slot_key(websocket: WebSocket) -> str:
    """Stable-enough slot key without identity (client host)."""
    client = websocket.client
    if client is None:
        return "unknown"
    return client.host or "unknown"
