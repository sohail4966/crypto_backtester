"""
Auth service — register and login (claim removed — BE-002/BE-024).
"""

from __future__ import annotations

import logging

import psycopg

from api.auth import (
    UnauthorizedError,
    create_access_token,
    hash_password,
    verify_password,
)
from api.exceptions import ValidationError
from api.repositories.user_repository import UserRepository, UserRow
from api.repositories.watchlist_repository import WatchlistRepository
from api.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from api.schemas.users import UserResponse
from api.services.symbol_service import SymbolService

logger = logging.getLogger(__name__)

# Users-email constraints that legitimately map to the anti-enumeration
# ``REGISTRATION_FAILED`` code. Everything else is a provisioning-side bug
# (e.g. watchlist default constraint) and gets its own code (BE-L2-008).
_EMAIL_UNIQUE_CONSTRAINTS = frozenset(
    {
        "uq_users_email_lower",
        "users_email_key",
        "users_email_lower_key",
    }
)


def _extract_constraint_name(exc: psycopg.errors.UniqueViolation) -> str:
    """Return the constraint name from a ``UniqueViolation`` diag, or ''."""
    diag = getattr(exc, "diag", None)
    if diag is None:
        return ""
    name = getattr(diag, "constraint_name", None)
    return name or ""


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

    def me(self, user: UserRow) -> UserResponse:
        """Return the authenticated user DTO (no password hash)."""
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _provision_default_watchlist(
        self,
        conn: psycopg.Connection,
        user_id,
        *,
        commit: bool = False,
    ) -> None:
        """Create default watchlist with active symbols (same as UserService.create)."""
        symbols = [s.symbol for s in self._symbols.list_symbols(conn, active_only=True)]
        watchlist = self._watchlists.create(
            conn,
            user_id=user_id,
            name="Default",
            is_default=True,
            sort_order=0,
            commit=commit,
        )
        if symbols:
            self._watchlists.set_symbols(conn, watchlist.id, symbols, commit=commit)

    def register(self, conn: psycopg.Connection, body: AuthRegisterRequest) -> AuthTokenResponse:
        """
        Create a user with password hash + default watchlist in one transaction.

        Commits once at the end (BE-012).
        """
        password_hash = hash_password(body.password)
        try:
            user = self._users.create_with_password(
                conn, body.name, body.email, password_hash, commit=False
            )
            self._provision_default_watchlist(conn, user.id, commit=False)
            conn.commit()
        except psycopg.errors.UniqueViolation as exc:
            conn.rollback()
            # BE-L2-008: distinguish the intended email-uniqueness path from a
            # provisioning-side unique violation (e.g. watchlist default).
            constraint = _extract_constraint_name(exc)
            if constraint and constraint not in _EMAIL_UNIQUE_CONSTRAINTS:
                logger.exception(
                    "Unexpected unique violation during register (constraint=%s)",
                    constraint,
                )
                raise ValidationError(
                    "PROVISIONING_CONFLICT",
                    "Registration failed due to a provisioning conflict",
                ) from exc
            # Anti-enumeration: generic conflict without confirming other fields (BE-024).
            raise ValidationError(
                "REGISTRATION_FAILED", "Unable to register with the provided email"
            ) from exc
        except Exception:
            conn.rollback()
            raise
        return self._token_response(user)

    def login(self, conn: psycopg.Connection, body: AuthLoginRequest) -> AuthTokenResponse:
        """Authenticate email/password and return a JWT.

        Timing side-channel: ``verify_password`` always runs a real bcrypt
        compare — even when ``user`` is missing — using a precomputed dummy
        hash (BE-L2-011). This keeps login latency uniform between known and
        unknown emails and pairs with BE-L2-010's per-IP/per-email limiter.
        """
        user = self._users.get_by_email(conn, body.email)
        candidate_hash = user.password_hash if user is not None else None
        password_ok = verify_password(body.password, candidate_hash)
        if user is None or not password_ok:
            raise UnauthorizedError("INVALID_CREDENTIALS", "Invalid email or password")
        return self._token_response(user)
