"""
Database connection helpers for TimescaleDB.

SQL lives in data.repository.queries; this module only opens connections.
"""

from __future__ import annotations

import os

import psycopg


def connection_string() -> str:
    """
    Return the PostgreSQL connection URL from the environment.

    Returns:
        DATABASE_URL if set, otherwise POSTGRES_* parts or the local Docker default.
    """
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit

    user = os.environ.get("POSTGRES_USER", "backtester")
    password = os.environ.get("POSTGRES_PASSWORD", "backtester")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    database = os.environ.get("POSTGRES_DB", "backtester")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def connect() -> psycopg.Connection:
    """
    Open a new database connection.

    Returns:
        An open psycopg connection. Caller must close it unless using a context manager.
    """
    return psycopg.connect(connection_string())
