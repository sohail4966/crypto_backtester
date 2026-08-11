"""
Password hashing and JWT helpers for Phase 11 auth.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from api import settings
from api.exceptions import ApiError


class UnauthorizedError(ApiError):
    """Missing or invalid credentials / token."""

    def __init__(self, code: str = "UNAUTHORIZED", message: str = "Unauthorized") -> None:
        super().__init__(code, message, status_code=401)


class ForbiddenError(ApiError):
    """Authenticated but not allowed for this resource."""

    def __init__(self, code: str = "FORBIDDEN", message: str = "Forbidden") -> None:
        super().__init__(code, message, status_code=403)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Args:
        password: Plaintext password.

    Returns:
        UTF-8 bcrypt hash string.
    """
    digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return digest.decode("utf-8")


# Precomputed dummy bcrypt hash used to normalise login timing when the
# candidate user is missing / has no password_hash (BE-L2-011). Computed once
# at import time with the current cost factor; keeps the "unknown email" branch
# in ``AuthService.login`` doing the same bcrypt work as the "known email"
# branch, closing the email-enumeration timing side-channel.
_DUMMY_BCRYPT_HASH: str = bcrypt.hashpw(
    b"login-timing-normaliser-unused", bcrypt.gensalt()
).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    When ``password_hash`` is ``None`` (or empty) the function still runs one
    bcrypt round against a module-level dummy hash and returns ``False`` — this
    keeps login latency uniform between "unknown email" and "wrong password"
    (BE-L2-011).

    Args:
        password: Candidate plaintext.
        password_hash: Stored hash, or None if unset.

    Returns:
        True when the password matches and ``password_hash`` is real.
    """
    target = password_hash or _DUMMY_BCRYPT_HASH
    try:
        matched = bcrypt.checkpw(password.encode("utf-8"), target.encode("utf-8"))
    except (ValueError, TypeError):
        matched = False
    return bool(matched and password_hash)


def create_access_token(*, user_id: UUID, email: str) -> str:
    """
    Issue an HS256 access token.

    Args:
        user_id: Subject user id.
        email: Email claim for debugging / clients.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes()),
    }
    return jwt.encode(payload, settings.jwt_secret(), algorithm=settings.jwt_algorithm())


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.

    Args:
        token: Bearer JWT.

    Returns:
        Token claims.

    Raises:
        UnauthorizedError: If the token is missing, expired, or invalid.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret(),
            algorithms=[settings.jwt_algorithm()],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("INVALID_TOKEN", "Invalid or expired token") from exc
