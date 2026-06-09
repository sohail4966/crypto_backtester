"""
FastAPI dependencies shared across routers.
"""

from __future__ import annotations

from collections.abc import Generator

import psycopg

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
