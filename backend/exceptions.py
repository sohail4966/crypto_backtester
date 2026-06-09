"""
Domain-specific exceptions for the crypto backtester.

Callers that need to handle data or signal failures distinctly should catch these
instead of broad Exception types.
"""


class DataGapError(Exception):
    """Raised when expected candles are missing from the database or date range."""


class InvalidSignalError(Exception):
    """Raised when a signal dict does not conform to the expected strategy schema."""


class MigrationError(Exception):
    """Raised when a database migration file is invalid or fails to apply."""
