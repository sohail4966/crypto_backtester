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
    ) -> None:
        self.id = id
        self.name = name
        self.email = email
        self.created_at = created_at
        self.updated_at = updated_at


def _row_to_user(row: tuple[Any, ...]) -> UserRow:
    """Map a database row to UserRow."""
    return UserRow(
        id=row[0],
        name=row[1],
        email=row[2],
        created_at=row[3],
        updated_at=row[4],
    )


class UserRepository:
    """CRUD operations on app.users."""

    def create(self, conn: psycopg.Connection, name: str, email: str) -> UserRow:
        """Insert a user and return the new row."""
        with conn.cursor() as cur:
            cur.execute(queries.INSERT_USER, (name, email))
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

    def delete(self, conn: psycopg.Connection, user_id: UUID) -> bool:
        """Delete user; cascades watchlists."""
        with conn.cursor() as cur:
            cur.execute(queries.DELETE_USER, (user_id,))
            conn.commit()
            return cur.rowcount > 0
