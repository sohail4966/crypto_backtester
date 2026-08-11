"""HTTP tests for Phase 10 AI endpoints (mock provider, no network)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.services.ai_service import reset_ai_service


@pytest.fixture(autouse=True)
def _force_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure CI never hits a live LLM."""
    monkeypatch.setenv("AI_LLM_PROVIDER", "mock")
    monkeypatch.delenv("AI_LLM_API_KEY", raising=False)
    reset_ai_service()
    yield
    reset_ai_service()


def test_post_translate_ok(client: TestClient) -> None:
    """POST /ai/translate returns a validated strategy."""
    response = client.post(
        "/api/v1/ai/translate",
        json={"text": "buy when daily RSI is oversold and price above 200 SMA"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["strategy"]["schema_version"] == "1"
    assert "explanation" in body


def test_post_translate_clarify_then_clarify(client: TestClient) -> None:
    """Ambiguous translate → clarify → ok."""
    first = client.post("/api/v1/ai/translate", json={"text": "buy when RSI is low"})
    assert first.status_code == 200
    payload = first.json()
    assert payload["status"] == "needs_clarification"
    session_id = payload["session_id"]
    assert payload["questions"]

    second = client.post(
        "/api/v1/ai/clarify",
        json={
            "session_id": session_id,
            "answers": {"rsi_oversold": "30", "rsi_period": "14"},
        },
    )
    assert second.status_code == 200
    done = second.json()
    assert done["status"] == "ok"
    assert done["strategy"]["entry"]["value"] == 30.0


def test_post_translate_invalid_dsl(client: TestClient) -> None:
    """Mock INVALID: path returns 422 INVALID_DSL."""
    response = client.post("/api/v1/ai/translate", json={"text": "INVALID: broken"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DSL"


def test_post_clarify_unknown_session(client: TestClient) -> None:
    """Unknown session → 404."""
    response = client.post(
        "/api/v1/ai/clarify",
        json={"session_id": "does-not-exist", "answers": {"a": "1"}},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_post_explain(client: TestClient) -> None:
    """POST /ai/explain returns English for a valid strategy."""
    response = client.post(
        "/api/v1/ai/explain",
        json={
            "strategy": {
                "schema_version": "1",
                "entry": {
                    "indicator": "RSI",
                    "params": {"period": 14},
                    "op": "<",
                    "value": 30,
                },
                "exit": {
                    "indicator": "RSI",
                    "params": {"period": 14},
                    "op": ">",
                    "value": 70,
                },
            }
        },
    )
    assert response.status_code == 200
    assert "RSI" in response.json()["explanation"]


def test_post_explain_invalid(client: TestClient) -> None:
    """Invalid strategy on explain → 422."""
    response = client.post(
        "/api/v1/ai/explain",
        json={"strategy": {"entry": {"not_a_valid_leaf": True}}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DSL"
