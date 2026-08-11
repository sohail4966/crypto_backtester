"""
User schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from api.schemas.auth import validate_email_format


class UserCreate(BaseModel):
    """
    Create user request.

    Password is required — passwordless create is disabled (BE-002).
    Prefer ``POST /auth/register`` for JWT issuance.
    """

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email_format(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return value.strip()


class UserUpdate(BaseModel):
    """Patch user request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_email_format(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class UserResponse(BaseModel):
    """User record (never includes password hash)."""

    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
