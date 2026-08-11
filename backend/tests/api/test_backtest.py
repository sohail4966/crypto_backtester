"""Tests for backtest HTTP API (Phase 4d)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from api.repositories.backtest_repository import BacktestRunRow
from api.repositories.symbol_repository import SymbolRow
from backtest.engine import Trade as EngineTrade
from backtest.types import BacktestConfig


def _sample_candles() -> pd.DataFrame:
    ts = pd.to_datetime(
        [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
            "2024-01-06",
            "2024-01-07",
            "2024-01-08",
        ],
        utc=True,
    )
    close = pd.Series([100.0, 102.0, 101.0, 105.0, 108.0, 107.0, 110.0, 112.0])
    return pd.DataFrame(
        {
            "ts": ts,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * len(close),
        }
    )


SIMPLE_STRATEGY = {
    "benchmark": "none",
    "entry": {"indicator": "RSI", "params": {"period": 2}, "op": "<", "value": 40},
    "exit": {"indicator": "RSI", "params": {"period": 2}, "op": ">", "value": 60},
}


def test_list_strategies(client: TestClient) -> None:
    """GET /backtest/strategies returns catalog entries from config.yaml."""
    response = client.get("/api/v1/backtest/strategies")
    assert response.status_code == 200
    body = response.json()
    assert "strategies" in body
    assert any(item["name"] == "full_stack_confluence" for item in body["strategies"])
    assert all(item["kind"] in {"dual", "long_only"} for item in body["strategies"])


@patch("api.deps.connect")
def test_post_backtest_xor_both_rejected(mock_connect: MagicMock, client: TestClient) -> None:
    """Both strategy_name and strategy → 422."""
    mock_connect.return_value = MagicMock()
    response = client.post(
        "/api/v1/backtest",
        json={
            "symbol": "BTC/USDT",
            "timeframe": "1d",
            "start": 1704067200,
            "end": 1706745600,
            "strategy_name": "full_stack_confluence",
            "strategy": SIMPLE_STRATEGY,
        },
    )
    assert response.status_code == 422


@patch("api.deps.connect")
def test_post_backtest_xor_neither_rejected(mock_connect: MagicMock, client: TestClient) -> None:
    """Neither strategy field → 422."""
    mock_connect.return_value = MagicMock()
    response = client.post(
        "/api/v1/backtest",
        json={
            "symbol": "BTC/USDT",
            "timeframe": "1d",
            "start": 1704067200,
            "end": 1706745600,
        },
    )
    assert response.status_code == 422


@patch("api.services.backtest_service.get_candles")
@patch("api.deps.connect")
def test_post_backtest_no_candles(
    mock_connect: MagicMock,
    mock_get_candles: MagicMock,
    client: TestClient,
) -> None:
    """Empty candle window → 422 NO_CANDLES."""
    mock_connect.return_value = MagicMock()
    mock_get_candles.return_value = pd.DataFrame()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.post(
            "/api/v1/backtest",
            json={
                "symbol": "BTC/USDT",
                "timeframe": "1d",
                "start": 1704067200,
                "end": 1706745600,
                "strategy": SIMPLE_STRATEGY,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_CANDLES"


@patch("api.services.backtest_service.BacktestRepository.insert")
@patch("api.services.backtest_service.get_candles")
@patch("api.deps.connect")
def test_post_backtest_inline_strategy(
    mock_connect: MagicMock,
    mock_get_candles: MagicMock,
    mock_insert: MagicMock,
    client: TestClient,
) -> None:
    """POST /backtest with inline strategy runs engine and persists."""
    mock_connect.return_value = MagicMock()
    candles = _sample_candles()
    mock_get_candles.return_value = candles
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    run_id = uuid4()

    def _insert(_conn: object, **kwargs: object) -> BacktestRunRow:
        return BacktestRunRow(
            run_id=run_id,
            symbol=str(kwargs["symbol"]),
            timeframe=str(kwargs["timeframe"]),
            start_ts=int(kwargs["start_ts"]),  # type: ignore[arg-type]
            end_ts=int(kwargs["end_ts"]),  # type: ignore[arg-type]
            initial_capital=float(kwargs["initial_capital"]),  # type: ignore[arg-type]
            strategy_name=None,
            strategy_config=dict(kwargs["strategy_config"]),  # type: ignore[arg-type]
            backtest_config=dict(kwargs["backtest_config"]),  # type: ignore[arg-type]
            metrics=dict(kwargs["metrics"]),  # type: ignore[arg-type]
            trades=list(kwargs["trades"]),  # type: ignore[arg-type]
            signals=list(kwargs["signals"]),  # type: ignore[arg-type]
            equity=list(kwargs["equity"]),  # type: ignore[arg-type]
            status="completed",
            error_message=None,
            user_id=None,
            created_at=now,
        )

    mock_insert.side_effect = _insert

    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.post(
            "/api/v1/backtest",
            json={
                "symbol": "BTC/USDT",
                "timeframe": "1d",
                "start": 1704067200,
                "end": 1706745600,
                "initial_capital": 10000,
                "strategy": SIMPLE_STRATEGY,
                "backtest": {
                    "slippage_bps": 0,
                    "commission": {"type": "percent", "rate": 0},
                    "sizing": {"mode": "full_capital"},
                },
            },
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["run_id"] == str(run_id)
    assert body["status"] == "completed"
    assert "metrics" in body
    assert "trade_count" in body["metrics"]
    assert isinstance(body["equity"], list)
    assert isinstance(body["signals"], list)
    assert isinstance(body["trades"], list)
    mock_insert.assert_called_once()
    inserted_config = mock_insert.call_args.kwargs["backtest_config"]
    assert inserted_config["export_trades"] is False


@patch("api.services.backtest_service.BacktestRepository.get")
@patch("api.deps.connect")
def test_get_backtest_404(mock_connect: MagicMock, mock_get: MagicMock, client: TestClient) -> None:
    """Unknown run → 404 RUN_NOT_FOUND."""
    mock_connect.return_value = MagicMock()
    mock_get.return_value = None
    response = client.get(f"/api/v1/backtest/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


@patch("api.services.backtest_service.BacktestRepository.get")
@patch("api.deps.connect")
def test_get_backtest_trades(
    mock_connect: MagicMock,
    mock_get: MagicMock,
    client: TestClient,
) -> None:
    """GET /backtest/{id}/trades returns detail log."""
    mock_connect.return_value = MagicMock()
    run_id = uuid4()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    mock_get.return_value = BacktestRunRow(
        run_id=run_id,
        symbol="BTC/USDT",
        timeframe="1d",
        start_ts=1704067200,
        end_ts=1706745600,
        initial_capital=10000.0,
        strategy_name=None,
        strategy_config={},
        backtest_config={},
        metrics={
            "total_return": 0.1,
            "win_rate": 1.0,
            "max_drawdown": 0.0,
            "trade_count": 1,
            "forced_close": False,
            "final_capital": 11000.0,
            "initial_capital": 10000.0,
        },
        trades=[
            {
                "entry_time": 1704153600,
                "exit_time": 1704240000,
                "entry_price": 100.0,
                "exit_price": 110.0,
                "side": "long",
                "exit_reason": "signal",
                "forced_close": False,
                "return_pct": 10.0,
                "size": 10000.0,
                "commission_paid": 0.0,
                "pnl_quote": 1000.0,
            }
        ],
        signals=[],
        equity=[],
        status="completed",
        error_message=None,
        user_id=None,
        created_at=now,
    )
    response = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(run_id)
    assert len(body["trades"]) == 1
    assert body["trades"][0]["side"] == "long"


@patch("api.services.chart_data_service.CandleService.get_candles")
@patch("api.services.backtest_service.BacktestRepository.get")
@patch("api.deps.connect")
def test_chart_data_with_run_id_overlays(
    mock_connect: MagicMock,
    mock_get_run: MagicMock,
    mock_candles: MagicMock,
    client: TestClient,
) -> None:
    """chart-data with runId + flags returns filtered markers."""
    from api.schemas.candles import Bar, CandlesResponse

    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    run_id = uuid4()
    mock_get_run.return_value = BacktestRunRow(
        run_id=run_id,
        symbol="BTC/USDT",
        timeframe="1h",
        start_ts=1704067200,
        end_ts=1704070800,
        initial_capital=10000.0,
        strategy_name=None,
        strategy_config={},
        backtest_config={},
        metrics={
            "total_return": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "trade_count": 1,
            "forced_close": False,
            "final_capital": 10000.0,
            "initial_capital": 10000.0,
        },
        trades=[
            {
                "entry_time": 1704067200,
                "exit_time": 1704070800,
                "entry_price": 1.0,
                "exit_price": 1.5,
                "side": "long",
                "exit_reason": "signal",
                "forced_close": False,
                "return_pct": 50.0,
                "size": 10000.0,
                "commission_paid": 0.0,
                "pnl_quote": 5000.0,
            }
        ],
        signals=[
            {"time": 1704067200, "side": "long", "label": "entry", "metadata": {}},
            {"time": 1704070800, "side": "long", "label": "exit", "metadata": {}},
        ],
        equity=[],
        status="completed",
        error_message=None,
        user_id=None,
        created_at=now,
    )
    mock_candles.return_value = CandlesResponse(
        symbol="BTC/USDT",
        timeframe="1h",
        bars=[
            Bar(time=1704067200, open=1, high=2, low=0.5, close=1.5, volume=10),
            Bar(time=1704070800, open=1.1, high=2.1, low=0.6, close=1.6, volume=11),
        ],
    )

    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "BTC/USDT",
                "timeframe": "1h",
                "start": 1704067200,
                "end": 1704070800,
                "includeSignals": "true",
                "includeTrades": "true",
                "runId": str(run_id),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["signals"]) == 2
    assert len(body["trades"]) == 2
    assert body["trades"][0]["metadata"]["event"] == "entry"


@patch("api.services.chart_data_service.CandleService.get_candles")
@patch("api.deps.connect")
def test_chart_data_without_run_id_stays_empty(
    mock_connect: MagicMock,
    mock_candles: MagicMock,
    client: TestClient,
) -> None:
    """include flags without runId still return empty overlays."""
    from api.schemas.candles import Bar, CandlesResponse

    mock_connect.return_value = MagicMock()
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    mock_candles.return_value = CandlesResponse(
        symbol="BTC/USDT",
        timeframe="1h",
        bars=[Bar(time=1704067200, open=1, high=2, low=0.5, close=1.5, volume=10)],
    )
    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "BTC/USDT",
                "timeframe": "1h",
                "start": 1704067200,
                "end": 1704070800,
                "includeSignals": "true",
                "includeTrades": "true",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["signals"] == []
    assert body["trades"] == []


@patch("api.services.chart_data_service.CandleService.get_candles")
@patch("api.services.backtest_service.BacktestRepository.get")
@patch("api.deps.connect")
def test_chart_data_unknown_run_id_404(
    mock_connect: MagicMock,
    mock_get_run: MagicMock,
    mock_candles: MagicMock,
    client: TestClient,
) -> None:
    """Unknown runId on chart-data → 404 RUN_NOT_FOUND."""
    from api.schemas.candles import Bar, CandlesResponse

    mock_connect.return_value = MagicMock()
    mock_get_run.return_value = None
    now = datetime(2024, 1, 1, tzinfo=UTC)
    symbol_row = SymbolRow("BTC/USDT", "BTC", "USDT", True, 1, now)
    mock_candles.return_value = CandlesResponse(
        symbol="BTC/USDT",
        timeframe="1h",
        bars=[Bar(time=1704067200, open=1, high=2, low=0.5, close=1.5, volume=10)],
    )
    with patch(
        "api.repositories.symbol_repository.SymbolRepository.get_symbol",
        return_value=symbol_row,
    ):
        response = client.get(
            "/api/v1/chart-data",
            params={
                "symbolId": "BTC/USDT",
                "timeframe": "1h",
                "start": 1704067200,
                "end": 1704070800,
                "includeTrades": "true",
                "runId": str(uuid4()),
            },
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_engine_trade_type_still_importable() -> None:
    """Sanity: Phase 3 Trade type remains the engine source of truth."""
    trade = EngineTrade(
        entry_date=pd.Timestamp("2024-01-01", tz="UTC"),
        exit_date=pd.Timestamp("2024-01-02", tz="UTC"),
        entry_price=100.0,
        exit_price=110.0,
        return_pct=10.0,
    )
    assert trade.side == "long"
    assert BacktestConfig(export_trades=False).export_trades is False
