"""
Auth service — register, login, claim.
"""

from __future__ import annotations

import psycopg

from api.auth import (
    UnauthorizedError,
    create_access_token,
    hash_password,
    verify_password,
)
from api.exceptions import NotFoundError, ValidationError
from api.repositories.user_repository import UserRepository, UserRow
from api.repositories.watchlist_repository import WatchlistRepository
from api.schemas.auth import (
    AuthClaimRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from api.services.symbol_service import SymbolService


class AuthService:
    """Password + JWT flows wrapping ``app.users``."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        watchlist_repository: WatchlistRepository | None = None,
        symbol_service: SymbolService | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._watchlists = watchlist_repository or WatchlistRepository()
        self._symbols = symbol_service or SymbolService()

    def _token_response(self, user: UserRow) -> AuthTokenResponse:
        """Build JWT envelope from a user row."""
        return AuthTokenResponse(
            access_token=create_access_token(user_id=user.id, email=user.email),
            user_id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _provision_default_watchlist(self, conn: psycopg.Connection, user_id) -> None:
        """Create default watchlist with active symbols (same as UserService.create)."""
        symbols = [s.symbol for s in self._symbols.list_symbols(conn, active_only=True)]
        watchlist = self._watchlists.create(
            conn,
            user_id=user_id,
            name="Default",
            is_default=True,
            sort_order=0,
        )
        if symbols:
            self._watchlists.set_symbols(conn, watchlist.id, symbols)

    def register(self, conn: psycopg.Connection, body: AuthRegisterRequest) -> AuthTokenResponse:
        """Create a user with password hash and return a JWT."""
        password_hash = hash_password(body.password)
        try:
            user = self._users.create_with_password(
                conn, body.name, body.email, password_hash
            )
        except psycopg.errors.UniqueViolation as exc:
            raise ValidationError(
                "EMAIL_EXISTS", f"Email already registered: {body.email}"
            ) from exc
        self._provision_default_watchlist(conn, user.id)
        return self._token_response(user)

    def login(self, conn: psycopg.Connection, body: AuthLoginRequest) -> AuthTokenResponse:
        """Authenticate email/password and return a JWT."""
        user = self._users.get_by_email(conn, body.email)
        if user is None or not verify_password(body.password, user.password_hash):
            raise UnauthorizedError("INVALID_CREDENTIALS", "Invalid email or password")
        return self._token_response(user)

    def claim(self, conn: psycopg.Connection, body: AuthClaimRequest) -> AuthTokenResponse:
        """
        Set a password on a legacy passwordless account once.

        Raises:
            NotFoundError: Unknown email.
            ValidationError: Password already set.
        """
        user = self._users.get_by_email(conn, body.email)
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", f"Unknown email: {body.email}")
        if user.password_hash:
            raise ValidationError(
                "PASSWORD_ALREADY_SET",
                "Password already set; use /auth/login",
            )
        updated = self._users.set_password_hash_if_null(
            conn, user.id, hash_password(body.password)
        )
        if updated is None:
            # Race: another claim won
            raise ValidationError(
                "PASSWORD_ALREADY_SET",
                "Password already set; use /auth/login",
            )
        return self._token_response(updated)
