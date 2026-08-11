"""
Auth endpoints — register, login, claim.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.schemas.auth import (
    AuthClaimRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from api.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_service = AuthService()


@router.post("/register", response_model=AuthTokenResponse, status_code=201)
def register(
    body: AuthRegisterRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> AuthTokenResponse:
    """Register a new user with password and return a JWT."""
    return _service.register(conn, body)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    body: AuthLoginRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> AuthTokenResponse:
    """Login with email and password."""
    return _service.login(conn, body)


@router.post("/claim", response_model=AuthTokenResponse)
def claim(
    body: AuthClaimRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> AuthTokenResponse:
    """Claim a legacy passwordless account by setting a password once."""
    return _service.claim(conn, body)
