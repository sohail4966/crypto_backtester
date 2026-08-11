"""
Repository for app.users CRUD.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from api.repositories import queries


class UserRow:
    """Row from app.users."""

    def __init__(
        self,
        id: UUID,
        name: str,
        email: str,
        created_at: datetime,
        updated_at: datetime,
        password_hash: str | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.updated_at = updated_at


def _row_to_user(row: tuple[Any, ...]) -> UserRow:
    """Map a database row to UserRow."""
    return UserRow(
        id=row[0],
        name=row[1],
        email=row[2],
        password_hash=row[3],
        created_at=row[4],
        updated_at=row[5],
    )


class UserRepository:
    """CRUD operations on app.users."""

    def create(self, conn: psycopg.Connection, name: str, email: str) -> UserRow:
        """Insert a passwordless user and return the new row."""
        with conn.cursor() as cur:
            cur.execute(queries.INSERT_USER, (name, email))
            row = cur.fetchone()
            conn.commit()
            assert row is not None
            return _row_to_user(row)

    def create_with_password(
        self,
        conn: psycopg.Connection,
        name: str,
        email: str,
        password_hash: str,
    ) -> UserRow:
        """Insert a user with a password hash."""
        with conn.cursor() as cur:
            cur.execute(queries.INSERT_USER_WITH_PASSWORD, (name, email, password_hash))
            row = cur.fetchone()
            conn.commit()
            assert row is not None
            return _row_to_user(row)

    def list_users(
        self,
        conn: psycopg.Connection,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserRow]:
        """List users with pagination."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_USERS, (limit, offset))
            return [_row_to_user(row) for row in cur.fetchall()]

    def get_by_id(self, conn: psycopg.Connection, user_id: UUID) -> UserRow | None:
        """Fetch user by primary key."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_USER_BY_ID, (user_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_user(row)

    def get_by_email(self, conn: psycopg.Connection, email: str) -> UserRow | None:
        """Fetch user by email."""
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_USER_BY_EMAIL, (email,))
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_user(row)

    def update(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        name: str | None,
        email: str | None,
    ) -> UserRow | None:
        """Patch user fields."""
        with conn.cursor() as cur:
            cur.execute(queries.UPDATE_USER, (name, email, user_id))
            row = cur.fetchone()
            conn.commit()
            if row is None:
                return None
            return _row_to_user(row)

    def set_password_hash_if_null(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        password_hash: str,
    ) -> UserRow | None:
        """Set password hash only when currently null (claim)."""
        with conn.cursor() as cur:
            cur.execute(queries.UPDATE_USER_PASSWORD_HASH, (password_hash, user_id))
            row = cur.fetchone()
            conn.commit()
            if row is None:
                return None
            return _row_to_user(row)

    def delete(self, conn: psycopg.Connection, user_id: UUID) -> bool:
        """Delete user; cascades watchlists."""
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_USER, (user_id,))
            conn.commit()
            return cur.rowcount > 0
