"""
Symbol catalog schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SymbolResponse(BaseModel):
    """Structured tradable symbol (Phase 4b v2 shape)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    ticker: str
    exchange: str
    base_asset: str = Field(alias="baseAsset")
    quote_asset: str = Field(alias="quoteAsset")
    tick_size: float = Field(alias="tickSize")
    lot_size: float = Field(alias="lotSize")
    asset_type: Literal["spot", "perp", "futures"] = Field(alias="type")
    active: bool
    sort_order: int = Field(alias="sortOrder")
    created_at: datetime | None = None

    # Phase 4 aliases (deprecated; kept for backward compatibility)
    symbol: str
    base: str
    quote: str
    is_active: bool
