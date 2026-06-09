"""
API runtime settings loaded from environment variables.
"""

from __future__ import annotations

import os


def api_host() -> str:
    """Return the bind host for uvicorn."""
    return os.environ.get("API_HOST", "0.0.0.0")


def api_port() -> int:
    """Return the bind port for uvicorn."""
    return int(os.environ.get("API_PORT", "8000"))


def cors_origins() -> list[str]:
    """Return allowed CORS origins for the chart client."""
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def candle_default_limit() -> int:
    """Default number of candles per historical request."""
    return int(os.environ.get("CANDLE_DEFAULT_LIMIT", "1000"))


def chart_data_default_limit() -> int:
    """Default number of bars per chart-data request (D-82)."""
    return int(os.environ.get("CHART_DATA_DEFAULT_LIMIT", "1500"))


def candle_max_limit() -> int:
    """Maximum candles per historical request."""
    return int(os.environ.get("CANDLE_MAX_LIMIT", "5000"))


def replay_max_window_bars() -> int:
    """Maximum bars allowed in a replay session window."""
    return int(os.environ.get("REPLAY_MAX_WINDOW_BARS", "50000"))


def replay_session_idle_minutes() -> int:
    """Minutes before an idle replay session is evicted."""
    return int(os.environ.get("REPLAY_SESSION_IDLE_MINUTES", "30"))


def replay_min_step_interval_ms() -> int:
    """Minimum milliseconds between autoplay bars."""
    return int(os.environ.get("REPLAY_MIN_STEP_INTERVAL_MS", "50"))
