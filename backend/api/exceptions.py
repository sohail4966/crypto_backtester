"""
API-specific exceptions mapped to HTTP error responses.
"""

from __future__ import annotations


class ApiError(Exception):
    """Base API error with HTTP status and machine-readable code."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ApiError):
    """Resource not found."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=404)


class ValidationError(ApiError):
    """Request or business validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=422)


class RateLimitError(ApiError):
    """Rate limit exceeded — mapped to HTTP 429 (BE-L2-009 / BE-L2-010)."""

    def __init__(self, code: str = "RATE_LIMITED", message: str = "Rate limit exceeded") -> None:
        super().__init__(code, message, status_code=429)
