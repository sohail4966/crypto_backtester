"""
Database connection helpers for TimescaleDB.

SQL lives in data.repository.queries; this module only opens connections.
"""

from __future__ import annotations

import os

import psycopg

# Port 5433 avoids clashing with a local Postgres install on the default 5432.
DEFAULT_DATABASE_URL = "postgresql://backtester:backtester@localhost:5433/backtester"


def connection_string() -> str:
    """
    Return the PostgreSQL connection URL from the environment.

    Returns:
        DATABASE_URL if set, otherwise the local Docker Compose default.
    """
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def connect() -> psycopg.Connection:
    """
    Open a new database connection.

    Returns:
        An open psycopg connection. Caller must close it unless using a context manager.
    """
    return psycopg.connect(connection_string())
