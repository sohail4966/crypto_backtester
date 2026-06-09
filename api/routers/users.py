"""
User CRUD endpoints.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.schemas.users import UserCreate, UserResponse, UserUpdate
from api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
_service = UserService()


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreate,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Create a user with a default watchlist."""
    return _service.create(conn, body)


@router.get("", response_model=list[UserResponse])
def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: psycopg.Connection = Depends(get_db),
) -> list[UserResponse]:
    """List users."""
    return _service.list_users(conn, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Fetch one user."""
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
