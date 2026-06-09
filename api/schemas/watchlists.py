"""
Watchlist schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):
    """Create watchlist request."""

    name: str = Field(min_length=1, max_length=200)
    symbols: list[str] = Field(default_factory=list)


class WatchlistUpdate(BaseModel):
    """Patch watchlist metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_default: bool | None = None
    sort_order: int | None = None


class WatchlistSymbolsUpdate(BaseModel):
    """Replace ordered symbols in a watchlist."""

    symbols: list[str]


class WatchlistResponse(BaseModel):
    """Watchlist with ordered symbols."""

    id: UUID
    user_id: UUID
    name: str
    is_default: bool
    sort_order: int
    symbols: list[str]
    created_at: datetime
