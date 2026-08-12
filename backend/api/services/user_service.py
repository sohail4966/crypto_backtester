"""
User management service.
"""

from __future__ import annotations

import logging
from uuid import UUID

import psycopg

from api.exceptions import NotFoundError, ValidationError
from api.repositories.user_repository import UserRepository, UserRow
from api.repositories.watchlist_repository import WatchlistRepository
from api.schemas.users import UserCreate, UserResponse, UserUpdate
from api.services.symbol_service import SymbolService

logger = logging.getLogger(__name__)

_EMAIL_UNIQUE_CONSTRAINTS = frozenset(
    {
        "uq_users_email_lower",
        "users_email_key",
        "users_email_lower_key",
    }
)


def _extract_constraint_name(exc: psycopg.errors.UniqueViolation) -> str:
    diag = getattr(exc, "diag", None)
    if diag is None:
        return ""
    name = getattr(diag, "constraint_name", None)
    return name or ""


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

    def _to_response(self, row: UserRow) -> UserResponse:
        """Map UserRow to API response."""
        return UserResponse(
            id=row.id,
            name=row.name,
            email=row.email,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def get_user_row(self, user: UserRow) -> UserResponse:
        """Map an already-loaded user row."""
        return self._to_response(user)

    def create(self, conn: psycopg.Connection, body: UserCreate) -> UserResponse:
        """Create a passwordless user and default watchlist in one transaction."""
        existing = self._users.get_by_email(conn, body.email)
        if existing is not None:
            return self._to_response(existing)
        try:
            user = self._users.create(conn, body.name, body.email, commit=False)
            symbols = [s.symbol for s in self._symbols.list_symbols(conn, active_only=True)]
            watchlist = self._watchlists.create(
                conn,
                user_id=user.id,
                name="Default",
                is_default=True,
                sort_order=0,
                commit=False,
            )
            if symbols:
                self._watchlists.set_symbols(conn, watchlist.id, symbols, commit=False)
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            conn.rollback()
            constraint = _extract_constraint_name(exc)
            if constraint and constraint not in _EMAIL_UNIQUE_CONSTRAINTS:
                logger.exception(
                    "Unexpected unique violation during user create (constraint=%s)",
                    constraint,
                )
                raise ValidationError(
                    "PROVISIONING_CONFLICT",
                    "User create failed due to a provisioning conflict",
                ) from exc
            raced = self._users.get_by_email(conn, body.email)
            if raced is not None:
                return self._to_response(raced)
            raise ValidationError(
                "CREATE_FAILED", "Unable to create user with the provided email"
            ) from exc
        except Exception:
            conn.rollback()
            raise

        return self._to_response(user)

    def list_users(
        self,
        conn: psycopg.Connection,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserResponse]:
        """List users (internal / admin — HTTP enumeration removed)."""
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
            constraint = _extract_constraint_name(exc)
            if constraint and constraint not in _EMAIL_UNIQUE_CONSTRAINTS:
                logger.exception(
                    "Unexpected unique violation during user update (constraint=%s)",
                    constraint,
                )
                raise ValidationError(
                    "PROVISIONING_CONFLICT",
                    "User update failed due to a provisioning conflict",
                ) from exc
            raise ValidationError(
                "UPDATE_FAILED", "Unable to update with the provided email"
            ) from exc
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")
        return self._to_response(user)

    def delete_user(self, conn: psycopg.Connection, user_id: UUID) -> None:
        """Delete user."""
        if not self._users.delete(conn, user_id):
            raise NotFoundError("USER_NOT_FOUND", f"Unknown user: {user_id}")
