# Tech Design — BE Phase 4d: Backtest HTTP API

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Engine** | [PHASE_3_HLD.md](../../../backend/docs/PHASE_3_HLD.md) — consume as-is |
| **Prior API notes** | [PHASE_4B_HLD.md](../../../backend/docs/PHASE_4B_HLD.md) deferred backtest/trades |
| **OpenAPI** | [openapi.yaml](../../../backend/docs/openapi.yaml) — bump to **0.5.0** |
| **Agent D** | Database + FastAPI + tests + OpenAPI |
| **Agent E** | Thin `/backtest` page + `backtestApi.ts` (low risk) |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
POST /api/v1/backtest
        │
        ▼
┌───────────────────┐     ┌──────────────────────┐
│ BacktestService   │────▶│ config.yaml catalog  │
│  resolve strategy │     │ get_candles (loader) │
│  evaluate signals │     │ evaluate_*           │
│  run_backtest     │     │ backtest.engine      │
│  compute_metrics  │     │ compute_metrics      │
└─────────┬─────────┘     └──────────────────────┘
          │
          ▼
┌───────────────────┐     GET /backtest/{id}
│ BacktestRepository│────▶GET /backtest/{id}/trades
│ app.backtest_runs │
└─────────┬─────────┘
          │
          ▼
GET /chart-data?runId=…&includeSignals&includeTrades
  ChartDataService loads markers for window from same table
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **API service** | HTTP validation, orchestration, persistence, marker mapping | Fill/sizing/risk math |
| **Phase 3 engine** | Trades, equity series, D-14 fills | HTTP, DB rows |
| **chart-data** | Window filter of stored markers | Re-running strategies live |

---

## 2. Database

### Migration `V008__backtest_runs.sql`

```sql
CREATE TABLE IF NOT EXISTS app.backtest_runs (
    run_id           UUID PRIMARY KEY,
    symbol           TEXT             NOT NULL REFERENCES app.symbols (symbol),
    timeframe        TEXT             NOT NULL,
    start_ts         BIGINT           NOT NULL,
    end_ts           BIGINT           NOT NULL,
    initial_capital  DOUBLE PRECISION NOT NULL,
    strategy_name    TEXT,
    strategy_config  JSONB            NOT NULL,
    backtest_config  JSONB            NOT NULL,
    metrics          JSONB            NOT NULL,
    trades           JSONB            NOT NULL DEFAULT '[]',
    signals          JSONB            NOT NULL DEFAULT '[]',
    equity           JSONB            NOT NULL DEFAULT '[]',
    status           TEXT             NOT NULL DEFAULT 'completed',
    error_message    TEXT,
    user_id          UUID             REFERENCES app.users (id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol_created
  ON app.backtest_runs (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user_id
  ON app.backtest_runs (user_id);
```

**Notes**

- `trades` JSONB = full round-trip trade log (API trade detail schema).
- `signals` / chart trade **markers** also stored as JSONB arrays matching `api.schemas.chart_data.Signal` / `Trade` so chart-data can read without recompute.
- `equity` = `[{ "time": <unix>, "value": <float> }, …]` aligned to candle `ts`.
- `status` reserved for future async (`completed` only in v1).

---

## 3. Backend modules

```
backend/
  data/migrations/sql/V008__backtest_runs.sql
  config.py                          # + list_strategies / load_strategy_by_name / default_backtest_config
  api/
    routers/backtest.py              # NEW
    schemas/backtest.py              # NEW
    services/backtest_service.py     # NEW — orchestration
    repositories/backtest_repository.py
    repositories/queries.py          # + SQL
    services/chart_data_service.py   # load markers when runId set
    routers/chart_data.py            # + runId query
    main.py                          # include router; version 0.5.0
  docs/openapi.yaml                  # document paths
  tests/api/test_backtest.py         # NEW
  tests/api/test_chart_data.py       # extend overlay cases
```

### Do not modify

- `backtest/engine.py`, fills, risk, sizing, metrics formulas (call only).
- Replay OverlayPipeline (stays indicators-only).

### Config helpers (additive)

```python
def list_named_strategies(path=None) -> list[dict]  # [{name, kind}]
def load_named_strategy(name, path=None) -> DualStrategy | Strategy
def load_default_backtest_config(path=None) -> BacktestConfig
```

---

## 4. REST contract

Base: `/api/v1`. Error envelope unchanged.

### `GET /backtest/strategies`

**200** `{ "strategies": [ { "name": "full_stack_confluence", "kind": "dual" } ] }`

### `POST /backtest` → `201`

**Body**

| Field | Required | Notes |
|---|---|---|
| `symbol` | yes | Must be active `app.symbols` |
| `timeframe` | yes | Supported TF |
| `start` / `end` | yes | Unix seconds inclusive window |
| `initial_capital` | no | Default `10000` or config.yaml |
| `strategy_name` | XOR | Catalog name |
| `strategy` | XOR | Inline YAML-compatible object |
| `backtest` | no | `{ slippage_bps, commission, sizing }` — defaults from config |
| `user_id` | no | Nullable FK |

**Response (snake_case)**

```json
{
  "run_id": "…",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "end": 1706745600,
  "initial_capital": 10000.0,
  "strategy_name": "full_stack_confluence",
  "status": "completed",
  "metrics": {
    "total_return": 0.12,
    "win_rate": 0.55,
    "max_drawdown": 0.08,
    "trade_count": 10,
    "forced_close": false,
    "final_capital": 11200.0,
    "initial_capital": 10000.0,
    "sharpe_ratio": 1.2,
    "sortino_ratio": 1.5,
    "calmar_ratio": 0.9,
    "profit_factor": 1.4,
    "benchmark_return": 0.05,
    "alpha_vs_benchmark": 0.07
  },
  "equity": [{"time": 1704067200, "value": 10000.0}],
  "signals": [{"time": 1704153600, "side": "long", "label": "entry", "metadata": {}}],
  "trades": [{"time": 1704153600, "side": "long", "price": 42000.0, "metadata": {"event": "entry", "trade_index": 0}}],
  "created_at": "2026-08-11T00:00:00Z"
}
```

Chart `trades` markers = **entry and exit events** (two markers per round-trip). Detail log uses a richer schema on `GET …/trades`.

### `GET /backtest/{run_id}` → `200`

Same shape as create response (full summary).

### `GET /backtest/{run_id}/trades` → `200`

```json
{
  "run_id": "…",
  "trades": [
    {
      "entry_time": 1704153600,
      "exit_time": 1704240000,
      "entry_price": 42000.0,
      "exit_price": 43000.0,
      "side": "long",
      "exit_reason": "signal",
      "forced_close": false,
      "return_pct": 2.38,
      "size": 10000.0,
      "commission_paid": 8.4,
      "pnl_quote": 238.0
    }
  ]
}
```

### Chart-data extension

| Param | Notes |
|---|---|
| `runId` | Optional UUID. When set with include flags, load markers from `app.backtest_runs`. |
| `includeSignals` / `includeTrades` | If false, return `[]` for that array even if `runId` set. |
| Missing / unknown `runId` | If `runId` provided but not found → `404 RUN_NOT_FOUND`. If omitted → `[]` as today. |

Filter: include markers with `time` in `[start, end]` of the chart request (inclusive).

---

## 5. Orchestration algorithm

```
1. Resolve strategy (name XOR inline); validate via existing _validate_strategy
2. Merge BacktestConfig defaults + request overrides (no CSV export side effect on API path)
3. require_active_symbol(symbol)
4. start_iso / end_iso from unix → UTC dates (inclusive)
5. candles = get_candles(symbol, timeframe, start_iso, end_iso)
6. if empty → ValidationError NO_CANDLES
7. Evaluate dual vs long-only (is_dual_strategy)
8. trades, equity = run_backtest(...)
9. metrics = compute_metrics(...); optional benchmark
10. Build detail trade JSON + chart Signal/Trade markers + equity points
11. INSERT backtest_runs; return response
```

**Marker mapping**

- **Signals:** for each True bar in entry/exit series (after edge trigger already applied by evaluator), emit `{time, side, label: "entry"|"exit"}`. Dual strategies use long/short sides.
- **Chart trades:** for each `Trade`, emit entry marker (`event=entry`) and exit marker (`event=exit`, include `exit_reason`, `return_pct`, `pnl_quote`).

**API path must not write** `output/trades.csv` or equity PNG (set export off / skip disk IO).

---

## 6. Frontend (Agent E)

Thin page only:

| File | Change |
|---|---|
| `services/backtestApi.ts` | listStrategies, runBacktest, getBacktest, getBacktestTrades |
| `types/backtest.ts` | DTO types + normalize |
| `pages/BacktestPage.tsx` | Form: symbol, TF, strategy select, start/end date, capital → POST → show metrics table + trades |

No chart overlay wiring on `/` in this phase (markers available via API for later FE). Update placeholder copy that still says “Phase 4c”.

---

## 7. Testing plan (Agent D)

| Test | Assert |
|---|---|
| `test_list_strategies` | ≥1 strategy from config |
| `test_post_backtest_named_strategy` | 201, run_id, metrics keys; repository insert mocked or DB |
| `test_post_backtest_xor_validation` | both/neither → 422 |
| `test_get_backtest_404` | unknown UUID |
| `test_get_trades` | shape |
| `test_no_candles` | 422 NO_CANDLES |
| `test_chart_data_with_run_id` | non-empty when flags true; empty when false |
| Existing API suite | still green |

Prefer mocking `get_candles` + engine for unit speed; one service-level test with synthetic candles is enough for AC-9 wrap proof.

---

## 8. OpenAPI / versioning

- App + OpenAPI `info.version`: **0.5.0**
- New tag `backtest`
- Fix chart-data description (“empty until 4d” → “populated when `runId` provided”)
- Document `runId` query param

---

## 9. Decisions baked in (from answers)

1. Sync only; no job queue.
2. `strategy_name` XOR `strategy`.
3. chart-data needs `runId` for markers.
4. Persist both detail trades and chart markers at write time.
5. Wire casing: snake_case for new backtest JSON; `runId` query alias on chart-data.
6. Thin FE page in scope for Agent E.
7. Workspace sync deferred (not this phase).
8. Max window: no hard bar cap beyond practical timeout; reject `start > end`.

---

## 10. Agent split

| Agent | Work |
|---|---|
| **D** | Migration, config helpers, repository, service, router, chart-data hook, OpenAPI, pytest |
| **E** | Thin BacktestPage + API client stubs/types |
| **F** | Review/fix D |
| **G** | Review/fix E |
| **H** | E2E pytest + ROADMAP + completion report |
