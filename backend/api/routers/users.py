"""
User CRUD endpoints.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from api.deps import get_current_user, get_db, require_same_user
from api.repositories.user_repository import UserRow
from api.schemas.common import ErrorBody, ErrorResponse
from api.schemas.users import UserResponse, UserUpdate
from api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
_service = UserService()


@router.post("", status_code=status.HTTP_410_GONE)
async def create_user(_request: Request) -> JSONResponse:
    """
    Removed (BE-L2-019). Onboarding lives only in ``POST /auth/register``,
    which returns a JWT and provisions the default watchlist in one
    transaction, and is protected by the anonymous-register rate limiter
    (BE-L2-010).
    """
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content=ErrorResponse(
            error=ErrorBody(
                code="GONE",
                message="POST /users is disabled; use POST /auth/register",
            )
        ).model_dump(),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current: UserRow = Depends(get_current_user)) -> UserResponse:
    """Authenticated current-user bootstrap (alias of ``GET /auth/me``)."""
    return _service.get_user_row(current)


@router.get("", status_code=status.HTTP_410_GONE)
def list_users(
    _limit: int = Query(default=100, ge=1, le=500),
    _offset: int = Query(default=0, ge=0),
    _current: UserRow = Depends(get_current_user),
) -> JSONResponse:
    """User enumeration removed (BE-016)."""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content=ErrorResponse(
            error=ErrorBody(
                code="GONE",
                message="GET /users enumeration is disabled; use GET /auth/me",
            )
        ).model_dump(),
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> UserResponse:
    """Fetch one user (JWT + same-user only)."""
    require_same_user(user_id, current)
    return _service.get_user(conn, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> UserResponse:
    """Update user name or email (owner only)."""
    require_same_user(user_id, current)
    return _service.update_user(conn, user_id, body)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
    current: UserRow = Depends(get_current_user),
) -> None:
    """Delete user and cascaded watchlists (owner only)."""
    require_same_user(user_id, current)
    _service.delete_user(conn, user_id)
