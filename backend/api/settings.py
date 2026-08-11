"""
API runtime settings loaded from environment variables.
"""

from __future__ import annotations

import os

# Known insecure placeholders — rejected even when explicitly set in non-dev.
_INSECURE_JWT_SECRETS = frozenset(
    {
        "dev-only-change-me-crypto-backtester",
        "change-me",
        "secret",
        "jwt-secret",
    }
)
_DEV_JWT_DEFAULT = "dev-only-change-me-crypto-backtester"


def app_env() -> str:
    """
    Application environment: ``dev`` | ``local`` | ``staging`` | ``prod``.

    Reads ``APP_ENV`` then ``ENV``. Missing/unknown values default to ``prod``
    (fail-closed). Local insecure defaults require an explicit ``APP_ENV=dev``
    or ``APP_ENV=local`` (G-001).
    """
    raw = (os.environ.get("APP_ENV") or os.environ.get("ENV") or "").strip().lower()
    if not raw:
        return "prod"
    if raw in ("development", "dev"):
        return "dev"
    if raw == "local":
        return "local"
    if raw in ("staging", "stage"):
        return "staging"
    if raw in ("prod", "production"):
        return "prod"
    # Unknown labels are treated as non-dev (fail-closed).
    return "prod"


def is_dev_env() -> bool:
    """True only when APP_ENV/ENV is explicitly ``dev`` or ``local``."""
    return app_env() in ("dev", "local")


def api_host() -> str:
    """Return the bind host for uvicorn."""
    return os.environ.get("API_HOST", "0.0.0.0")


def api_port() -> int:
    """Return the bind port for uvicorn."""
    # Render and other PaaS hosts inject PORT; API_PORT remains for local overrides.
    return int(os.environ.get("PORT") or os.environ.get("API_PORT", "8000"))


def cors_origins() -> list[str]:
    """
    Return allowed CORS origins for the chart client.

    Dev/local: defaults to Vite/CRA localhost when ``CORS_ORIGINS`` is unset.
    Staging/prod: ``CORS_ORIGINS`` must be set explicitly (G-006); empty list
    only when the variable is present but blank (API-only / no browser CORS).
    """
    if "CORS_ORIGINS" in os.environ:
        raw = os.environ.get("CORS_ORIGINS", "")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    if is_dev_env():
        return ["http://localhost:5173", "http://localhost:3000"]
    raise RuntimeError(
        "CORS_ORIGINS must be set when APP_ENV/ENV is not explicitly dev/local. "
        "Refusing to default to localhost origins outside development."
    )


def cors_allow_localhost_regex() -> str | None:
    """
    Optional regex for local SPA dev (Vite may use 5173, 5174, … when ports are taken).

    Default: enabled only when ``APP_ENV``/``ENV`` is ``dev``/``local``.
    Override with ``CORS_ALLOW_LOCALHOST=true|false``.
    """
    raw = os.environ.get("CORS_ALLOW_LOCALHOST")
    if raw is not None:
        enabled = raw.lower() in ("1", "true", "yes", "on")
    else:
        enabled = is_dev_env()
    if not enabled:
        return None
    return r"http://(localhost|127\.0\.0\.1)(:\d+)?"


def candle_default_limit() -> int:
    """Default number of candles per historical request."""
    return int(os.environ.get("CANDLE_DEFAULT_LIMIT", "1000"))


def chart_data_default_limit() -> int:
    """Default number of bars per chart-data request (D-82)."""
    return int(os.environ.get("CHART_DATA_DEFAULT_LIMIT", "1500"))


def candle_max_limit() -> int:
    """Maximum candles per historical request."""
    return int(os.environ.get("CANDLE_MAX_LIMIT", "5000"))


def scan_max_symbols() -> int:
    """Maximum symbols allowed per scan request."""
    return int(os.environ.get("SCAN_MAX_SYMBOLS", "50"))


def backtest_max_window_sec() -> int:
    """Maximum inclusive backtest window length in seconds."""
    return int(os.environ.get("BACKTEST_MAX_WINDOW_SEC", str(365 * 24 * 3600)))


def ai_max_rpm() -> int:
    """Max AI requests per minute per user (in-process limiter)."""
    return int(os.environ.get("AI_MAX_RPM", "30"))


def ws_max_connections_per_user() -> int:
    """Max concurrent live/replay WS connections per authenticated user."""
    return int(os.environ.get("WS_MAX_CONNECTIONS_PER_USER", "5"))


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


def ai_llm_provider() -> str | None:
    """Optional explicit LLM provider name (``mock`` | ``openai_compat``)."""
    raw = os.environ.get("AI_LLM_PROVIDER", "").strip()
    return raw or None


def ai_llm_api_key() -> str | None:
    """LLM API key from environment (never commit secrets)."""
    raw = os.environ.get("AI_LLM_API_KEY", "").strip()
    return raw or None


def ai_llm_base_url() -> str:
    """OpenAI-compatible API base URL."""
    return os.environ.get("AI_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def ai_llm_model() -> str:
    """Model id for chat completions."""
    return os.environ.get("AI_LLM_MODEL", "gpt-4o-mini")


def ai_llm_timeout_sec() -> float:
    """HTTP timeout for LLM calls."""
    return float(os.environ.get("AI_LLM_TIMEOUT_SEC", "60"))


def ai_clarify_ttl_minutes() -> float:
    """Idle TTL for clarification sessions."""
    return float(os.environ.get("AI_CLARIFY_TTL_MINUTES", "30"))


def jwt_secret() -> str:
    """
    HS256 signing secret for access tokens.

    In ``dev``/``local``: allows a clearly labeled default when unset.
    In staging/prod: ``JWT_SECRET`` is required and must not be a known placeholder.
    """
    raw = os.environ.get("JWT_SECRET")
    if raw is not None:
        secret = raw.strip()
    else:
        secret = ""

    if is_dev_env():
        if not secret:
            return _DEV_JWT_DEFAULT
        return secret

    if not secret:
        raise RuntimeError(
            "JWT_SECRET must be set when APP_ENV/ENV is not dev/local. "
            "Refusing to start with a forgeable default."
        )
    if secret in _INSECURE_JWT_SECRETS or secret.startswith("dev-only-"):
        raise RuntimeError(
            "JWT_SECRET is a known insecure placeholder; set a strong unique secret."
        )
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters in non-dev environments.")
    return secret


def validate_security_settings() -> None:
    """
    Fail closed at startup for non-dev misconfiguration.

    Call from application lifespan / factory so workers refuse to serve.
    Outside explicit ``dev``/``local``: strong ``JWT_SECRET`` and explicit
    ``CORS_ORIGINS`` are required (G-001 / G-006).
    """
    # Force evaluation (raises on bad config).
    jwt_secret()
    if not is_dev_env():
        cors_origins()


def jwt_algorithm() -> str:
    """JWT signing algorithm (HS256)."""
    return os.environ.get("JWT_ALGORITHM", "HS256")


def jwt_expire_minutes() -> int:
    """Access token lifetime in minutes (default 7 days)."""
    return int(os.environ.get("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))


def live_ws_poll_interval_ms() -> int:
    """Milliseconds between live WS DB-tail polls."""
    return int(os.environ.get("LIVE_WS_POLL_INTERVAL_MS", "2000"))


def redis_url() -> str | None:
    """
    Optional Redis connection URL for the shared rate limiter (BE-L2-009).

    When unset (dev / single-worker deploys) the API falls back to the
    in-process rate limiter. Multi-worker deployments SHOULD set this to a
    reachable Redis instance so per-user AI RPM, WS slot counts, anonymous
    registration limits, and WS tickets converge across workers.
    """
    raw = (os.environ.get("REDIS_URL") or "").strip()
    return raw or None


def auth_register_ip_rpm() -> int:
    """Per-IP anonymous registration attempts per minute (BE-L2-010)."""
    return int(os.environ.get("AUTH_REGISTER_IP_RPM", "5"))


def auth_register_email_rph() -> int:
    """Per-email anonymous registration attempts per hour (BE-L2-010)."""
    return int(os.environ.get("AUTH_REGISTER_EMAIL_RPH", "3"))


def trust_proxy_headers() -> bool:
    """
    When ``true`` the API trusts ``X-Forwarded-For`` for ``_client_ip`` (BE-L2-010).

    Only enable behind a proxy that scrubs client-supplied XFF; otherwise a
    caller can spoof their apparent IP and bypass per-IP rate limits.
    """
    return os.environ.get("TRUST_PROXY_HEADERS", "false").strip().lower() in ("1", "true", "yes", "on")


def ws_ticket_ttl_seconds() -> int:
    """One-shot WS ticket TTL (BE-for-FE-L2-003)."""
    return int(os.environ.get("WS_TICKET_TTL_SECONDS", "60"))
