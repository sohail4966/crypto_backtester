"""
Shared Pydantic models for API responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorBody
