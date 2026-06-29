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
    # Render and other PaaS hosts inject PORT; API_PORT remains for local overrides.
    return int(os.environ.get("PORT") or os.environ.get("API_PORT", "8000"))


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
    """Minimum milliseconds between autoplay bars (legacy; client owns clock in v2)."""
    return int(os.environ.get("REPLAY_MIN_STEP_INTERVAL_MS", "50"))


def replay_trail_bars() -> int:
    """Max visible bars kept behind the replay cursor (default 500)."""
    return int(os.environ.get("REPLAY_TRAIL_BARS", "500"))


def replay_prefetch_bars() -> int:
    """Bars preloaded and precomputed ahead of the cursor (default 1000)."""
    return int(os.environ.get("REPLAY_PREFETCH_BARS", "1000"))


def replay_extend_threshold() -> int:
    """Trigger forward DB fetch when cursor is within this many bars of prefetch edge."""
    return int(os.environ.get("REPLAY_EXTEND_THRESHOLD", "200"))


def replay_tick_batch_size() -> int:
    """Max ticks per ``tick_batch`` WS message and per ``refill`` request."""
    return int(os.environ.get("REPLAY_TICK_BATCH_SIZE", "100"))


def replay_tick_refill_threshold() -> int:
    """Client-side hint: send ``refill`` when local queue depth drops below this."""
    return int(os.environ.get("REPLAY_TICK_REFILL_THRESHOLD", "20"))


def replay_base_interval_ms() -> int:
    """Client playback base interval at 1× speed (1 bar per second)."""
    return int(os.environ.get("REPLAY_BASE_INTERVAL_MS", "1000"))


def replay_min_interval_ms() -> int:
    """Client playback floor interval (20 bars/sec cap at 50 ms)."""
    return int(os.environ.get("REPLAY_MIN_INTERVAL_MS", "50"))


def replay_checkpoint_interval_sec() -> int:
    """Seconds between automatic cursor checkpoints to ``app.replay_sessions``."""
    return int(os.environ.get("REPLAY_CHECKPOINT_INTERVAL_SEC", "30"))
