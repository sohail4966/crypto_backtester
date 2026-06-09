"""
User schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Create user request."""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)


class UserUpdate(BaseModel):
    """Patch user request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320)


class UserResponse(BaseModel):
    """User record."""

    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
