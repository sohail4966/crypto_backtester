"""
User management service.
"""

from __future__ import annotations

from uuid import UUID

import psycopg

from api.exceptions import NotFoundError, ValidationError
from api.repositories.user_repository import UserRepository
from api.repositories.watchlist_repository import WatchlistRepository
from api.schemas.users import UserCreate, UserResponse, UserUpdate
from api.services.symbol_service import SymbolService


class UserService:
    """CRUD for users and default watchlist provisioning."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        watchlist_repository: WatchlistRepository | None = None,
        symbol_service: SymbolService | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._watchlists = watchlist_repository or WatchlistRepository()
        self._symbols = symbol_service or SymbolService()

    def _to_response(self, row: object) -> UserResponse:
        """Map UserRow to API response."""
        return UserResponse(
            id=row.id,
            name=row.name,
            email=row.email,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(self, conn: psycopg.Connection, body: UserCreate) -> UserResponse:
        """Create user and default watchlist with all active symbols."""
        try:
            user = self._users.create(conn, body.name, body.email)
        except psycopg.errors.UniqueViolation as exc:
            raise ValidationError("EMAIL_EXISTS", f"Email already registered: {body.email}") from exc

        symbols = [s.symbol for s in self._symbols.list_symbols(conn, active_only=True)]
        watchlist = self._watchlists.create(
            conn,
            user_id=user.id,
            name="Default",
            is_default=True,
            sort_order=0,
        )
        if symbols:
            self._watchlists.set_symbols(conn, watchlist.id, symbols)

        return self._to_response(user)

    def list_users(
        self,
        conn: psycopg.Connection,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserResponse]:
        """List users."""
        return [self._to_response(row) for row in self._users.list_users(conn, limit, offset)]

    def get_user(self, conn: psycopg.Connection, user_id: UUID) -> UserResponse:
        """Fetch one user."""
        user = self._users.get_by_id(conn, user_id)
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")
        return self._to_response(user)

    def update_user(
        self,
        conn: psycopg.Connection,
        user_id: UUID,
        body: UserUpdate,
    ) -> UserResponse:
        """Patch user fields."""
        try:
            user = self._users.update(conn, user_id, body.name, body.email)
        except psycopg.errors.UniqueViolation as exc:
            raise ValidationError("EMAIL_EXISTS", "Email already registered") from exc
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")
        return self._to_response(user)

    def delete_user(self, conn: psycopg.Connection, user_id: UUID) -> None:
        """Delete user."""
        if not self._users.delete(conn, user_id):
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")
