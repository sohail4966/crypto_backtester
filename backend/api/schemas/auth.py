"""
Auth request/response schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    """Register a new user with password."""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class AuthLoginRequest(BaseModel):
    """Login with email + password."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class AuthClaimRequest(BaseModel):
    """Claim a legacy passwordless account by setting a password once."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class AuthTokenResponse(BaseModel):
    """JWT access token envelope."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    name: str
    created_at: datetime
    updated_at: datetime
