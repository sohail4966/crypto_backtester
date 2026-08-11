"""Tests for API settings hardening (BE-003 / BE-017 / G-001 / G-006)."""

from __future__ import annotations

import pytest

from api import settings


def test_app_env_defaults_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    assert settings.app_env() == "prod"
    assert not settings.is_dev_env()


def test_app_env_requires_explicit_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    assert settings.app_env() == "dev"
    assert settings.is_dev_env()


def test_jwt_secret_allows_dev_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    assert settings.jwt_secret() == "dev-only-change-me-crypto-backtester"


def test_jwt_secret_fails_closed_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
        settings.jwt_secret()


def test_jwt_secret_fails_closed_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
        settings.jwt_secret()


def test_jwt_secret_rejects_placeholder_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "dev-only-change-me-crypto-backtester")
    with pytest.raises(RuntimeError, match="insecure placeholder"):
        settings.jwt_secret()


def test_cors_localhost_default_off_outside_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("CORS_ALLOW_LOCALHOST", raising=False)
    assert settings.cors_allow_localhost_regex() is None


def test_cors_localhost_default_on_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("CORS_ALLOW_LOCALHOST", raising=False)
    assert settings.cors_allow_localhost_regex() is not None


def test_cors_origins_default_localhost_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert "http://localhost:5173" in settings.cors_origins()


def test_cors_origins_required_outside_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be set"):
        settings.cors_origins()


def test_cors_origins_explicit_empty_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("CORS_ORIGINS", "")
    assert settings.cors_origins() == []


def test_validate_security_settings_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    settings.validate_security_settings()
