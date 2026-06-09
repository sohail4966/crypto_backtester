"""
Symbol catalog schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SymbolResponse(BaseModel):
    """Single tradable symbol from app.symbols."""

    symbol: str
    base: str
    quote: str
    is_active: bool
    sort_order: int
    created_at: datetime | None = None
