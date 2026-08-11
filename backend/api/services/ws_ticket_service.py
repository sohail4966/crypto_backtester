"""
One-shot WebSocket ticket store (BE-for-FE-L2-003).

The FE trades a long-lived JWT for a short-lived opaque ticket, then attaches
it to WebSocket handshakes as ``?ticket=<value>``. Tickets are single-use and
scoped by TTL, which keeps JWTs out of URLs (leaks into DevTools/HAR/history)
and shortens the exposure window for ``localStorage`` residue.

Backend backends:
  1. In-process TTL cache — always available; used for dev/tests and any
     deployment where ``REDIS_URL`` is unset. Correct only within a single
     worker; documented in ``.env.example`` alongside the rate-limiter fallback.
  2. Redis (plug-in point kept for BE-L2-009's Redis backend). The current
     façade defaults to in-process; wiring Redis is a swap in
     ``get_ws_ticket_service()``.

Every ticket is minted, stored, and consumed within the API process. The API
never accepts client-supplied ticket values that aren't already known — so a
missing/expired/consumed ticket returns ``None`` from ``consume``.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass
from uuid import UUID

from api import settings

logger = logging.getLogger(__name__)


@dataclass
class _TicketEntry:
    user_id: UUID
    expires_at: float


class WsTicketService:
    """
    In-process ticket store. Thread-safe; consume is single-shot (pop).

    NOTE: In multi-worker deployments this is per-worker. Callers must live
    with the fallout (a ticket minted on worker A cannot be consumed on
    worker B). Ops runbook documents the ``--workers 1`` fallback and the
    ``REDIS_URL`` recommended path.
    """

    def __init__(self) -> None:
        self._store: dict[str, _TicketEntry] = {}
        self._lock = threading.Lock()

    def issue(self, user_id: UUID, *, ttl_sec: int | None = None) -> tuple[str, int]:
        """
        Mint a single-use opaque ticket for ``user_id``.

        Returns:
            ``(ticket, expires_in)`` — 128 hex chars, seconds-until-expiry.
        """
        ttl = ttl_sec if ttl_sec is not None else settings.ws_ticket_ttl_seconds()
        ticket = secrets.token_hex(32)
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._prune_locked(time.monotonic())
            self._store[ticket] = _TicketEntry(user_id=user_id, expires_at=expires_at)
        return ticket, ttl

    def consume(self, ticket: str) -> UUID | None:
        """
        Consume a ticket, returning the owner ``user_id`` or ``None`` if the
        ticket is unknown / expired / already used.
        """
        if not ticket:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._store.pop(ticket, None)
        if entry is None:
            return None
        if entry.expires_at < now:
            return None
        return entry.user_id

    # --- test / metrics helpers -------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def reset(self) -> None:
        """Wipe all outstanding tickets (tests only)."""
        with self._lock:
            self._store.clear()

    def _prune_locked(self, now: float) -> None:
        """Drop expired tickets while holding the lock."""
        expired = [t for t, e in self._store.items() if e.expires_at < now]
        for t in expired:
            self._store.pop(t, None)


_service: WsTicketService | None = None
_service_lock = threading.Lock()


def get_ws_ticket_service() -> WsTicketService:
    """Return the process-wide ticket service singleton."""
    global _service
    if _service is not None:
        return _service
    with _service_lock:
        if _service is None:
            _service = WsTicketService()
        return _service


def reset_ws_ticket_service() -> None:
    """Reset the singleton (tests only)."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.reset()
        _service = None
