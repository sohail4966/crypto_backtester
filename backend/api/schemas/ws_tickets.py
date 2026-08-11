"""
WebSocket ticket schemas (BE-for-FE-L2-003).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WsTicketResponse(BaseModel):
    """Response for ``POST /api/v1/ws/tickets``."""

    ticket: str = Field(description="Opaque single-use ticket (128 hex chars).")
    expires_in: int = Field(description="Seconds until the ticket expires (default 60).")
