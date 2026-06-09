"""
Tests for meta endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Health returns status and version."""
    response = client.get("/api/v1/meta/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.4.1"
    assert body["database"] in {"ok", "error"}


def test_timeframes_endpoint(client: TestClient) -> None:
    """Timeframes lists supported resolutions."""
    response = client.get("/api/v1/meta/timeframes")
    assert response.status_code == 200
    timeframes = response.json()["timeframes"]
    assert "1m" in timeframes
    assert "3m" in timeframes
    assert "30m" in timeframes
    assert "2h" in timeframes
    assert "1h" in timeframes
    assert "1d" in timeframes
    assert "1w" in timeframes
    assert "1M" in timeframes
