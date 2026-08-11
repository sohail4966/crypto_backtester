"""
WebSocket ticket router (BE-for-FE-L2-003).

`POST /api/v1/ws/tickets` — JWT-required. Returns a short-lived opaque ticket
usable as ``?ticket=<value>`` on the replay / live WebSocket handshakes so the
JWT never lives in a WebSocket URL.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.repositories.user_repository import UserRow
from api.schemas.ws_tickets import WsTicketResponse
from api.services.ws_ticket_service import get_ws_ticket_service

router = APIRouter(prefix="/ws", tags=["ws-tickets"])


@router.post("/tickets", response_model=WsTicketResponse, status_code=201)
def create_ws_ticket(current: UserRow = Depends(get_current_user)) -> WsTicketResponse:
    """
    Issue a single-use, short-lived WebSocket ticket for the JWT subject.

    The FE calls this immediately before every WS connect and uses the
    returned ticket as ``?ticket=<value>``. Tickets expire after
    ``WS_TICKET_TTL_SECONDS`` (default 60s) and are consumed on the first
    handshake. Legacy ``?token=<jwt>`` / ``Authorization: Bearer`` remain
    supported on the WebSocket endpoints for one release window.
    """
    ticket, expires_in = get_ws_ticket_service().issue(current.id)
    return WsTicketResponse(ticket=ticket, expires_in=expires_in)
