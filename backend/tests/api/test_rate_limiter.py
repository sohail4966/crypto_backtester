"""Tests for the rate-limiter façade (BE-L2-009, BE-L2-010)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from api.rate_limiter import (
    InProcessRateLimiter,
    RateLimitDeniedError,
    check_ai_rpm,
    reset_rate_limiter,
)


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_rate_limiter()
    yield
    reset_rate_limiter()


def test_in_process_rpm_denies_over_limit() -> None:
    limiter = InProcessRateLimiter()
    for _ in range(3):
        limiter.check_rpm("ns", "k", limit=3, window_sec=60)
    with pytest.raises(RateLimitDeniedError):
        limiter.check_rpm("ns", "k", limit=3, window_sec=60)


def test_in_process_slot_acquire_release_symmetric() -> None:
    limiter = InProcessRateLimiter()
    limiter.acquire_slot("ws", "user", max_slots=1)
    assert limiter.slot_count("ws", "user") == 1
    with pytest.raises(RateLimitDeniedError):
        limiter.acquire_slot("ws", "user", max_slots=1)
    limiter.release_slot("ws", "user")
    assert limiter.slot_count("ws", "user") == 0
    limiter.release_slot("ws", "user")
    assert limiter.slot_count("ws", "user") == 0


@patch("api.settings.ai_max_rpm", return_value=2)
def test_ai_rpm_denies_over_limit(_mock_rpm: object) -> None:
    reset_rate_limiter()
    check_ai_rpm("127.0.0.1")
    check_ai_rpm("127.0.0.1")
    with pytest.raises(Exception) as exc_info:
        check_ai_rpm("127.0.0.1")
    assert getattr(exc_info.value, "code", "") == "RATE_LIMITED"
