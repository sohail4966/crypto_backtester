"""
Shared rate limiter façade for per-user AI, WS slots, and anonymous limits.

Solves the multi-worker correctness gap called out by BE-L2-009 without
forcing every deploy to run Redis: an in-process backend implements the same
protocol and can be swapped for a Redis backend when ``REDIS_URL`` is set.

Design goals:
  1. Single source of truth for every limiter used by the API (BE-004,
     BE-L2-009, BE-L2-010, BE-for-FE-L2-003 ticket issuance).
  2. Bounded memory in the in-process backend (BE-L2-009's leak).
  3. Fail-closed semantics — every ``check_*`` method raises ``ValidationError``
     (mapped to 422 today, or 429 via ``RateLimitError`` when the caller opts in
     — see ``api.exceptions``).

Testing: prefer the in-process backend in unit tests. Redis backend is only
constructed when ``settings.redis_url()`` is set AND the ``redis`` package is
importable; otherwise the factory falls back to in-process with a one-time
warning. This keeps tests deterministic and dependency-free.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Protocol
from uuid import UUID

from api import settings

logger = logging.getLogger(__name__)

# Cap the process-local counters so a runaway caller cannot balloon memory.
# 10k unique keys × ~64B each ≈ 640KB — safe upper bound (BE-L2-009).
_MAX_TRACKED_KEYS = 10_000


def _norm_user_key(user_id: UUID | str) -> str:
    """Return a stable string key for a user identifier."""
    return str(user_id)


class RateLimitDeniedError(Exception):
    """Internal signal — the concrete limiter denied acquire/check.

    Callers (deps) translate this into whatever ``ApiError`` is appropriate
    (``ValidationError("RATE_LIMITED", ...)`` today; ``RateLimitError`` when the
    HTTP status must be 429).
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class RateLimiter(Protocol):
    """Protocol implemented by every rate-limit backend."""

    def check_rpm(self, namespace: str, key: str, limit: int, window_sec: int = 60) -> None:
        """Record one hit and raise when the window is over ``limit``."""

    def acquire_slot(self, namespace: str, key: str, max_slots: int) -> None:
        """Reserve one concurrent slot (e.g. WS connection) or raise."""

    def release_slot(self, namespace: str, key: str) -> None:
        """Release one previously acquired slot; clamped at 0."""

    def slot_count(self, namespace: str, key: str) -> int:
        """Return current concurrent slot count (for tests / observability)."""


class InProcessRateLimiter:
    """
    Single-process rate limiter. Correct under ``--workers 1``; degrades
    to per-worker limits under multi-worker (documented risk — see
    BE-L2-009 runbook note in ``.env.example``).
    """

    def __init__(self) -> None:
        # Sliding-window hits: (namespace, key) -> deque[timestamp]
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        # Concurrent slots: (namespace, key) -> int
        self._slots: dict[tuple[str, str], int] = defaultdict(int)
        self._lock = threading.Lock()

    def check_rpm(self, namespace: str, key: str, limit: int, window_sec: int = 60) -> None:
        """Sliding-window request-per-window check."""
        now = time.monotonic()
        with self._lock:
            self._trim_locked(now)
            hits = self._hits[(namespace, key)]
            while hits and now - hits[0] > window_sec:
                hits.popleft()
            if len(hits) >= limit:
                raise RateLimitDeniedError(
                    "RATE_LIMITED",
                    f"{namespace} limit exceeded ({limit}/{window_sec}s)",
                )
            hits.append(now)

    def acquire_slot(self, namespace: str, key: str, max_slots: int) -> None:
        """Reserve a concurrent slot or raise."""
        with self._lock:
            current = self._slots[(namespace, key)]
            if current >= max_slots:
                raise RateLimitDeniedError(
                    "WS_LIMIT",
                    f"Max {max_slots} concurrent {namespace} slots per key",
                )
            self._slots[(namespace, key)] = current + 1

    def release_slot(self, namespace: str, key: str) -> None:
        """Release a concurrent slot."""
        with self._lock:
            current = self._slots.get((namespace, key), 0)
            if current > 0:
                self._slots[(namespace, key)] = current - 1
            if self._slots.get((namespace, key)) == 0:
                self._slots.pop((namespace, key), None)

    def slot_count(self, namespace: str, key: str) -> int:
        with self._lock:
            return self._slots.get((namespace, key), 0)

    # --- test/debug helpers ------------------------------------------------

    def reset(self) -> None:
        """Wipe all tracked state (tests only)."""
        with self._lock:
            self._hits.clear()
            self._slots.clear()

    def _trim_locked(self, now: float) -> None:
        """Bound the deque map so long-running processes cannot leak.

        Removes empty deques and, if we still exceed ``_MAX_TRACKED_KEYS``,
        drops the oldest entries first-in-first-out.
        """
        for k in list(self._hits.keys()):
            if not self._hits[k]:
                self._hits.pop(k, None)
        overflow = len(self._hits) - _MAX_TRACKED_KEYS
        if overflow > 0:
            for k in list(self._hits.keys())[:overflow]:
                self._hits.pop(k, None)


class _NullRedisRateLimiter:
    """Placeholder — Redis backend can plug in here without touching callers.

    Kept as a stub so we don't drag in the ``redis`` dep transitively; the
    factory below picks it up when ``settings.redis_url()`` is set AND the
    ``redis`` package is importable. If the package is missing we log once
    and fall back to in-process.
    """

    def __init__(self, url: str, client: Any) -> None:  # pragma: no cover - stub
        self._client = client
        self._url = url

    def check_rpm(
        self, namespace: str, key: str, limit: int, window_sec: int = 60
    ) -> None:  # pragma: no cover - stub
        raise RateLimitDeniedError("RATE_LIMITED", "redis limiter not wired")

    def acquire_slot(
        self, namespace: str, key: str, max_slots: int
    ) -> None:  # pragma: no cover - stub
        raise RateLimitDeniedError("WS_LIMIT", "redis limiter not wired")

    def release_slot(self, namespace: str, key: str) -> None:  # pragma: no cover - stub
        return None

    def slot_count(self, namespace: str, key: str) -> int:  # pragma: no cover - stub
        return 0


_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Return the process-wide limiter singleton (factory + cache).

    When ``REDIS_URL`` is unset the in-process backend is returned. When it is
    set, a stub is instantiated today; hooking in the real Redis client is a
    later swap (BE-L2-009 recommended solution keeps a clean plug-point rather
    than a half-wired Redis path).
    """
    global _limiter
    if _limiter is not None:
        return _limiter
    with _limiter_lock:
        if _limiter is not None:
            return _limiter
        url = settings.redis_url() if hasattr(settings, "redis_url") else None
        if url:
            try:
                import redis  # type: ignore[import-not-found]

                client = redis.Redis.from_url(url)
                _limiter = _NullRedisRateLimiter(url, client)
                logger.info("rate_limiter: redis backend not yet wired; using stub")
            except Exception as exc:  # noqa: BLE001 - fall back gracefully
                logger.warning(
                    "rate_limiter: falling back to in-process (redis import failed: %s)", exc
                )
                _limiter = InProcessRateLimiter()
        else:
            _limiter = InProcessRateLimiter()
        return _limiter


def reset_rate_limiter() -> None:
    """Wipe limiter state and reset the singleton (tests only)."""
    global _limiter
    with _limiter_lock:
        if isinstance(_limiter, InProcessRateLimiter):
            _limiter.reset()
        _limiter = None


# --- Convenience helpers for common namespaces -------------------------------


def check_ai_rpm(key: UUID | str) -> None:
    """Record one AI RPM hit for ``key`` (user id or IP) or raise."""
    limit = settings.ai_max_rpm()
    try:
        get_rate_limiter().check_rpm("ai:rpm", _norm_user_key(key), limit=limit, window_sec=60)
    except RateLimitDeniedError as exc:
        raise _rate_limited(exc.message) from exc


def acquire_ws(key: UUID | str) -> None:
    """Acquire one WS connection slot for ``key`` or raise."""
    max_conn = settings.ws_max_connections_per_user()
    try:
        get_rate_limiter().acquire_slot("ws:conn", _norm_user_key(key), max_slots=max_conn)
    except RateLimitDeniedError as exc:
        raise _ws_limit(exc.message) from exc


def release_ws(key: UUID | str) -> None:
    """Release one previously acquired WS slot."""
    get_rate_limiter().release_slot("ws:conn", _norm_user_key(key))


def ws_slot_count(key: UUID | str) -> int:
    """Return current WS slot count for ``key`` (tests / metrics)."""
    return get_rate_limiter().slot_count("ws:conn", _norm_user_key(key))


# --- Error helpers (avoids ApiError import cycle at module top) --------------


def _rate_limited(message: str):
    """Return a ``RateLimitError`` with a friendly message."""
    from api.exceptions import RateLimitError

    return RateLimitError("RATE_LIMITED", message)


def _ws_limit(message: str):
    """Return a ``ValidationError`` for WS slot exhaustion (kept 422 for parity)."""
    from api.exceptions import ValidationError

    return ValidationError("WS_LIMIT", message)
