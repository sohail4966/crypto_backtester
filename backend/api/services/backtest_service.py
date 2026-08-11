"""
Backtest HTTP orchestration — wraps the Phase 3 CLI engine (Phase 4d).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
import psycopg

from api.exceptions import NotFoundError, ValidationError
from api.repositories.backtest_repository import BacktestRepository, BacktestRunRow
from api.schemas.backtest import (
    BacktestCreateRequest,
    BacktestMetricsResponse,
    BacktestParamsBody,
    BacktestRunResponse,
    BacktestTradesResponse,
    EquityPoint,
    StrategiesResponse,
    StrategyInfo,
    TradeDetail,
)
from api.schemas.chart_data import Signal, Trade
from api.services.symbol_service import SymbolService
from api.services.timeframes import validate_timeframe
from backtest.benchmark import compute_buy_and_hold_return
from backtest.engine import Trade as EngineTrade
from backtest.engine import run_backtest
from backtest.metrics import compute_metrics
from backtest.types import BacktestConfig, CommissionConfig, SizingConfig
from config import (
    get_strategy_benchmark,
    is_dual_strategy,
    list_named_strategies,
    load_default_backtest_config,
    load_default_initial_capital,
    load_named_strategy,
    validate_strategy,
)
from data.loader import get_candles
from exceptions import InvalidSignalError
from indicators.registry import INDICATORS
from signals.evaluator import evaluate_dual_strategy, evaluate_signals
from signals.types import DualStrategy, Strategy


def _unix_to_iso_date(ts: int) -> str:
    """Convert unix seconds to a UTC ISO date string for ``get_candles``."""
    return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


def _ts_to_unix(value: pd.Timestamp | datetime) -> int:
    """Convert a pandas/py datetime to unix seconds UTC."""
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    else:
        stamp = stamp.tz_convert("UTC")
    return int(stamp.timestamp())


def _merge_backtest_config(
    defaults: BacktestConfig,
    overrides: BacktestParamsBody | None,
) -> BacktestConfig:
    """Merge request overrides onto config.yaml defaults; never export CSV."""
    slippage = defaults.slippage_bps
    commission = defaults.commission
    sizing = defaults.sizing
    if overrides is not None:
        if overrides.slippage_bps is not None:
            slippage = float(overrides.slippage_bps)
        if overrides.commission is not None:
            commission = CommissionConfig(
                type=overrides.commission.type,
                rate=float(overrides.commission.rate),
                amount=float(overrides.commission.amount),
            )
        if overrides.sizing is not None:
            sizing = SizingConfig(
                mode=overrides.sizing.mode,
                pct=float(overrides.sizing.pct),
                amount=float(overrides.sizing.amount),
                risk_pct=float(overrides.sizing.risk_pct),
            )
    return BacktestConfig(
        slippage_bps=slippage,
        commission=commission,
        sizing=sizing,
        export_trades=False,
        trades_csv=defaults.trades_csv,
    )


def _backtest_config_dict(config: BacktestConfig) -> dict[str, Any]:
    """JSON-serializable snapshot of simulation knobs."""
    return {
        "slippage_bps": config.slippage_bps,
        "commission": {
            "type": config.commission.type,
            "rate": config.commission.rate,
            "amount": config.commission.amount,
        },
        "sizing": {
            "mode": config.sizing.mode,
            "pct": config.sizing.pct,
            "amount": config.sizing.amount,
            "risk_pct": config.sizing.risk_pct,
        },
        "export_trades": False,
    }


def _signals_from_series(
    candles: pd.DataFrame,
    series: pd.Series,
    *,
    side: str,
    label: str,
) -> list[dict[str, Any]]:
    """Emit chart signal markers for True bars in a boolean series."""
    markers: list[dict[str, Any]] = []
    aligned = series.reindex(candles.index).fillna(False).astype(bool)
    for idx, flag in enumerate(aligned):
        if not flag:
            continue
        markers.append(
            {
                "time": _ts_to_unix(candles.iloc[idx]["ts"]),
                "side": side,
                "label": label,
                "metadata": {},
            }
        )
    return markers


def _build_chart_signals(
    candles: pd.DataFrame,
    *,
    entry: pd.Series,
    exit_: pd.Series,
    short_entry: pd.Series | None = None,
    short_exit: pd.Series | None = None,
) -> list[dict[str, Any]]:
    """Build chart signal markers from evaluator boolean series."""
    markers = _signals_from_series(candles, entry, side="long", label="entry")
    markers.extend(_signals_from_series(candles, exit_, side="long", label="exit"))
    if short_entry is not None:
        markers.extend(_signals_from_series(candles, short_entry, side="short", label="entry"))
    if short_exit is not None:
        markers.extend(_signals_from_series(candles, short_exit, side="short", label="exit"))
    markers.sort(key=lambda item: (item["time"], item["label"], item["side"]))
    return markers


def _trade_detail(trade: EngineTrade) -> dict[str, Any]:
    """Serialize one engine trade to the detail log schema."""
    return {
        "entry_time": _ts_to_unix(trade.entry_date),
        "exit_time": _ts_to_unix(trade.exit_date),
        "entry_price": float(trade.entry_price),
        "exit_price": float(trade.exit_price),
        "side": trade.side,
        "exit_reason": trade.exit_reason,
        "forced_close": bool(trade.forced_close),
        "return_pct": float(trade.return_pct),
        "size": float(trade.size),
        "commission_paid": float(trade.commission_paid),
        "pnl_quote": float(trade.pnl_quote),
    }


def _chart_trade_markers(trades: list[EngineTrade]) -> list[dict[str, Any]]:
    """Emit entry + exit chart markers for each round-trip."""
    markers: list[dict[str, Any]] = []
    for index, trade in enumerate(trades):
        markers.append(
            {
                "time": _ts_to_unix(trade.entry_date),
                "side": trade.side,
                "price": float(trade.entry_price),
                "metadata": {"event": "entry", "trade_index": index},
            }
        )
        markers.append(
            {
                "time": _ts_to_unix(trade.exit_date),
                "side": trade.side,
                "price": float(trade.exit_price),
                "metadata": {
                    "event": "exit",
                    "trade_index": index,
                    "exit_reason": trade.exit_reason,
                    "return_pct": float(trade.return_pct),
                    "pnl_quote": float(trade.pnl_quote),
                    "forced_close": bool(trade.forced_close),
                },
            }
        )
    return markers


def _equity_points(candles: pd.DataFrame, equity: pd.Series) -> list[dict[str, Any]]:
    """Align equity samples to candle timestamps."""
    points: list[dict[str, Any]] = []
    length = min(len(candles), len(equity))
    for idx in range(length):
        points.append(
            {
                "time": _ts_to_unix(candles.iloc[idx]["ts"]),
                "value": float(equity.iloc[idx]),
            }
        )
    return points


def _metrics_payload(metrics: dict[str, Any]) -> dict[str, Any]:
    """Normalize metrics dict for JSON storage / response."""
    payload = {
        "total_return": float(metrics["total_return"]),
        "win_rate": float(metrics["win_rate"]),
        "max_drawdown": float(metrics["max_drawdown"]),
        "trade_count": int(metrics["trade_count"]),
        "forced_close": bool(metrics["forced_close"]),
        "final_capital": float(metrics["final_capital"]),
        "initial_capital": float(metrics["initial_capital"]),
    }
    for key in (
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "profit_factor",
        "benchmark_return",
        "alpha_vs_benchmark",
    ):
        if key in metrics:
            value = metrics[key]
            payload[key] = None if value is None else float(value)
    return payload


def filter_markers_in_window(
    markers: list[dict[str, Any]],
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    """Keep markers whose ``time`` falls in ``[start, end]`` inclusive."""
    return [item for item in markers if start <= int(item.get("time", -1)) <= end]


class BacktestService:
    """Run and retrieve persisted backtests via the Phase 3 engine."""

    def __init__(
        self,
        repository: BacktestRepository | None = None,
        symbol_service: SymbolService | None = None,
    ) -> None:
        self._repo = repository or BacktestRepository()
        self._symbols = symbol_service or SymbolService()

    def list_strategies(self) -> StrategiesResponse:
        """Return named strategies from config.yaml."""
        items = [StrategyInfo(name=item["name"], kind=item["kind"]) for item in list_named_strategies()]
        return StrategiesResponse(strategies=items)

    def _resolve_strategy(
        self,
        body: BacktestCreateRequest,
    ) -> tuple[str | None, Strategy | DualStrategy]:
        """Resolve XOR strategy inputs into a validated strategy dict."""
        if body.strategy_name:
            name = body.strategy_name.strip()
            try:
                strategy = load_named_strategy(name)
            except KeyError as exc:
                raise ValidationError("UNKNOWN_STRATEGY", str(exc)) from exc
            except ValueError as exc:
                raise ValidationError("INVALID_STRATEGY", str(exc)) from exc
            return name, strategy

        assert body.strategy is not None
        try:
            validate_strategy("inline", body.strategy)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ValidationError("INVALID_STRATEGY", str(exc)) from exc
        return None, body.strategy  # type: ignore[return-value]

    def run(self, conn: psycopg.Connection, body: BacktestCreateRequest) -> BacktestRunResponse:
        """
        Execute a backtest synchronously and persist the run.

        Raises:
            ValidationError: Bad inputs or empty candle window.
            NotFoundError: Unknown / inactive symbol.
        """
        try:
            validate_timeframe(body.timeframe)
        except ValueError as exc:
            raise ValidationError("INVALID_TIMEFRAME", str(exc)) from exc

        self._symbols.require_active_symbol(conn, body.symbol)
        strategy_name, strategy = self._resolve_strategy(body)

        defaults = load_default_backtest_config()
        backtest_config = _merge_backtest_config(defaults, body.backtest)
        initial_capital = (
            float(body.initial_capital)
            if body.initial_capital is not None
            else load_default_initial_capital()
        )

        start_iso = _unix_to_iso_date(body.start)
        end_iso = _unix_to_iso_date(body.end)
        candles = get_candles(body.symbol, body.timeframe, start_iso, end_iso)
        if candles.empty:
            raise ValidationError(
                "NO_CANDLES",
                f"No candles for {body.symbol} {body.timeframe} between {start_iso} and {end_iso}",
            )

        atr_series = None
        long_side = None
        short_side = None
        short_entry_signals = None
        short_exit_signals = None

        try:
            if is_dual_strategy(strategy):
                signals = evaluate_dual_strategy(candles, strategy)
                entry_signals = signals["long_entry"]
                exit_signals = signals["long_exit"]
                short_entry_signals = signals["short_entry"]
                short_exit_signals = signals["short_exit"]
                long_side = strategy["long"]
                short_side = strategy["short"]
                stop_loss = long_side.get("stop_loss") or {}
                atr_period = int(stop_loss.get("period", 14))
                atr_series = INDICATORS["ATR"](
                    candles["close"],
                    high=candles["high"],
                    low=candles["low"],
                    period=atr_period,
                )
            else:
                entry_signals, exit_signals = evaluate_signals(candles, strategy)
        except InvalidSignalError as exc:
            raise ValidationError("INVALID_STRATEGY", str(exc)) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("INVALID_STRATEGY", str(exc)) from exc

        engine_trades, equity = run_backtest(
            candles,
            entry_signals,
            exit_signals,
            initial_capital=initial_capital,
            short_entry_signals=short_entry_signals,
            short_exit_signals=short_exit_signals,
            long_side=long_side,
            short_side=short_side,
            atr_series=atr_series,
            backtest_config=backtest_config,
        )

        benchmark_return: float | None = None
        if get_strategy_benchmark(strategy) == "symbol":
            benchmark_return = compute_buy_and_hold_return(candles)

        metrics = compute_metrics(
            engine_trades,
            equity,
            candles=candles,
            timeframe=body.timeframe,
            benchmark_return=benchmark_return,
        )

        detail_trades = [_trade_detail(trade) for trade in engine_trades]
        chart_signals = _build_chart_signals(
            candles,
            entry=entry_signals,
            exit_=exit_signals,
            short_entry=short_entry_signals,
            short_exit=short_exit_signals,
        )
        chart_trades = _chart_trade_markers(engine_trades)
        equity_points = _equity_points(candles, equity)
        metrics_payload = _metrics_payload(metrics)

        run_id = uuid4()
        row = self._repo.insert(
            conn,
            run_id=run_id,
            symbol=body.symbol,
            timeframe=body.timeframe,
            start_ts=body.start,
            end_ts=body.end,
            initial_capital=initial_capital,
            strategy_name=strategy_name,
            strategy_config=dict(strategy),
            backtest_config=_backtest_config_dict(backtest_config),
            metrics=metrics_payload,
            trades=detail_trades,
            signals=chart_signals,
            equity=equity_points,
            status="completed",
            user_id=body.user_id,
        )
        return self._to_run_response(row, chart_trade_markers=chart_trades)

    def get_run(self, conn: psycopg.Connection, run_id: UUID) -> BacktestRunResponse:
        """Fetch a persisted run or raise ``RUN_NOT_FOUND``."""
        row = self._repo.get(conn, run_id)
        if row is None:
            raise NotFoundError("RUN_NOT_FOUND", f"Backtest run {run_id} not found")
        return self._to_run_response(row)

    def get_trades(self, conn: psycopg.Connection, run_id: UUID) -> BacktestTradesResponse:
        """Return the full round-trip trade log for a run."""
        row = self._repo.get(conn, run_id)
        if row is None:
            raise NotFoundError("RUN_NOT_FOUND", f"Backtest run {run_id} not found")
        trades = [TradeDetail.model_validate(item) for item in row.trades]
        return BacktestTradesResponse(run_id=row.run_id, trades=trades)

    def get_chart_overlays(
        self,
        conn: psycopg.Connection,
        run_id: UUID,
        *,
        start: int,
        end: int,
        include_signals: bool,
        include_trades: bool,
    ) -> tuple[list[Signal], list[Trade]]:
        """
        Load chart markers for a run filtered to a window.

        Raises:
            NotFoundError: When ``run_id`` does not exist.
        """
        row = self._repo.get(conn, run_id)
        if row is None:
            raise NotFoundError("RUN_NOT_FOUND", f"Backtest run {run_id} not found")

        signals: list[Signal] = []
        trades: list[Trade] = []
        if include_signals:
            for item in filter_markers_in_window(row.signals, start, end):
                signals.append(Signal.model_validate(item))
        if include_trades:
            # Detail trades are round-trips; chart markers are rebuilt from them.
            chart_markers = self._detail_to_chart_trades(row.trades)
            for item in filter_markers_in_window(chart_markers, start, end):
                trades.append(Trade.model_validate(item))
        return signals, trades

    @staticmethod
    def _detail_to_chart_trades(detail_trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rebuild entry/exit chart markers from persisted detail trades."""
        markers: list[dict[str, Any]] = []
        for index, trade in enumerate(detail_trades):
            markers.append(
                {
                    "time": int(trade["entry_time"]),
                    "side": trade.get("side"),
                    "price": float(trade["entry_price"]),
                    "metadata": {"event": "entry", "trade_index": index},
                }
            )
            markers.append(
                {
                    "time": int(trade["exit_time"]),
                    "side": trade.get("side"),
                    "price": float(trade["exit_price"]),
                    "metadata": {
                        "event": "exit",
                        "trade_index": index,
                        "exit_reason": trade.get("exit_reason"),
                        "return_pct": trade.get("return_pct"),
                        "pnl_quote": trade.get("pnl_quote"),
                        "forced_close": trade.get("forced_close"),
                    },
                }
            )
        return markers

    def _to_run_response(
        self,
        row: BacktestRunRow,
        *,
        chart_trade_markers: list[dict[str, Any]] | None = None,
    ) -> BacktestRunResponse:
        """Map a DB row to the API response model."""
        markers = chart_trade_markers
        if markers is None:
            markers = self._detail_to_chart_trades(row.trades)
        return BacktestRunResponse(
            run_id=row.run_id,
            symbol=row.symbol,
            timeframe=row.timeframe,
            start=row.start_ts,
            end=row.end_ts,
            initial_capital=row.initial_capital,
            strategy_name=row.strategy_name,
            status=row.status,
            metrics=BacktestMetricsResponse.model_validate(row.metrics),
            equity=[EquityPoint.model_validate(item) for item in row.equity],
            signals=[Signal.model_validate(item) for item in row.signals],
            trades=[Trade.model_validate(item) for item in markers],
            created_at=row.created_at,
        )
