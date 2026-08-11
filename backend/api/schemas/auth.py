"""
Auth request/response schemas.
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


class AuthRegisterRequest(BaseModel):
    """Register a new user with password."""

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


class AuthLoginRequest(BaseModel):
    """Login with email + password."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email_format(value)


class AuthTokenResponse(BaseModel):
    """JWT access token envelope."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    name: str
    created_at: datetime
    updated_at: datetime
