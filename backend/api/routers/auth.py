"""
Auth endpoints — register, login, me (claim removed — BE-002).
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_db
from api.repositories.user_repository import UserRow
from api.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from api.schemas.users import UserResponse
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


@router.get("/me", response_model=UserResponse)
def me(current: UserRow = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user (JWT proof for FE bootstrap)."""
    return _service.me(current)
