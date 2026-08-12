"""
User CRUD endpoints (no AuthN / AuthZ).
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from api.deps import get_db
from api.schemas.common import ErrorBody, ErrorResponse
from api.schemas.users import UserCreate, UserResponse, UserUpdate
from api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
_service = UserService()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Create a passwordless user and default watchlist."""
    return _service.create(conn, body)


@router.get("", status_code=status.HTTP_410_GONE)
def list_users(
    _limit: int = Query(default=100, ge=1, le=500),
    _offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """User enumeration remains disabled."""
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content=ErrorResponse(
            error=ErrorBody(
                code="GONE",
                message="GET /users enumeration is disabled; use GET /users/{id}",
            )
        ).model_dump(),
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Fetch one user by id."""
    return _service.get_user(conn, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Update user name or email."""
    return _service.update_user(conn, user_id, body)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> None:
    """Delete user and cascaded watchlists."""
    _service.delete_user(conn, user_id)
