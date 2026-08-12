"""
User schemas.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    """Strip and lowercase an email address."""
    return value.strip().lower()


def validate_email_format(value: str) -> str:
    """Normalize and validate email format."""
    email = normalize_email(value)
    if not _EMAIL_RE.match(email) or len(email) > 320:
        raise ValueError("Invalid email format")
    return email


class UserCreate(BaseModel):
    """Passwordless create — name + email only (no AuthN)."""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)

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
