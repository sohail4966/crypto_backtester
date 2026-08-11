"""
FastAPI application factory for Phase 4+ client API.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import settings
from api.exceptions import ApiError
from api.routers import (
    ai,
    auth,
    backtest,
    candles,
    chart_data,
    indicators,
    meta,
    replay,
    scan,
    symbols,
    users,
    watchlists,
)
from api.schemas.common import ErrorBody, ErrorResponse
from api.ws import live as live_ws
from api.ws import replay as replay_ws
from data.storage import run_migrations_on_startup


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Apply DB migrations on API startup."""
    run_migrations_on_startup()
    yield


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Returns:
        Configured FastAPI app with routers and exception handlers.
    """
    app = FastAPI(
        title="Crypto Backtester API",
        version="0.8.0",
        description=(
            "Chart client API — chart-data, candles, indicators, replay, "
            "backtest HTTP, screener scan, AI NL→DSL, JWT auth, and live candle WS."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_origin_regex=settings.cors_allow_localhost_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        """Map ApiError to JSON error envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message)).model_dump(),
        )

    api_prefix = "/api/v1"
    app.include_router(meta.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(symbols.router, prefix=api_prefix)
    app.include_router(chart_data.router, prefix=api_prefix)
    app.include_router(candles.router, prefix=api_prefix)
    app.include_router(indicators.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(watchlists.router, prefix=api_prefix)
    app.include_router(replay.router, prefix=api_prefix)
    app.include_router(backtest.router, prefix=api_prefix)
    app.include_router(scan.router, prefix=api_prefix)
    # Phase 10 AI — keep mounted; JWT optional (public in v1, see PHASE_11_HLD).
    app.include_router(ai.router, prefix=api_prefix)
    app.include_router(replay_ws.router)
    app.include_router(live_ws.router)

    return app


app = create_app()
