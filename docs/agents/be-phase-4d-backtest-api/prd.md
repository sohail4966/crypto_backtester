# PRD — BE Phase 4d: Backtest HTTP API

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 4d |
| **Product intent** | [ROADMAP.md — Phase 4d](../../../backend/docs/ROADMAP.md#phase-4d--backtest-http-api) |
| **Prior contracts** | [PHASE_4B_HLD.md](../../../backend/docs/PHASE_4B_HLD.md) (deferred trades/signals); [PHASE_3_HLD.md](../../../backend/docs/PHASE_3_HLD.md) (engine) |
| **Decisions** | D-14 (next-bar fills); D-69 (no auth); D-81 (unified chart-data); D-95 (4d = backtest HTTP) |

---

## 1. Problem / Goal

### Problem

The Phase 3 backtest engine only runs via CLI (`run_backtest.py`). Chart clients can load candles and indicators through Phase 4/4b/4c APIs, but `GET /chart-data` always returns empty `signals` / `trades`. There is no HTTP way to start a backtest, persist a run, or overlay trade markers on the chart.

### Goal

Expose the **existing** CLI backtest engine over REST:

1. `POST /api/v1/backtest` runs a strategy on a symbol/timeframe/window and persists the run.
2. Clients can fetch run summary, metrics, equity points, and the trade log by `run_id`.
3. `GET /chart-data` can return non-empty `signals` / `trades` when a persisted `runId` is supplied (and include flags are true).

Success looks like: a chart/backtest client can run a named or inline strategy, store the result, and render entry/exit markers from the same contract as Phase 4b chart-data — **without rewriting the engine**.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Analyst / trader (local chart client)** | Runs backtests from `/backtest` or future chart overlays; loads markers via chart-data. | None — public API (D-69). |
| **Developer / QA** | Hits OpenAPI `/docs`, pytest, and optional thin FE page. | Same — no auth. |

User-scoped “my runs” ownership is optional metadata only (`user_id` nullable). JWT ownership is Phase 11.

---

## 3. Scope

### In scope (v1)

- Migration `V008__backtest_runs.sql` → `app.backtest_runs`.
- Sync REST:
  - `POST /api/v1/backtest` — execute + persist + return summary
  - `GET /api/v1/backtest/{run_id}` — metrics, equity, summary trades/signals
  - `GET /api/v1/backtest/{run_id}/trades` — full trade log
  - `GET /api/v1/backtest/strategies` — list named strategies from server `config.yaml`
- Strategy input: **`strategyName`** (server catalog) **XOR** inline **`strategy`** dict (same schema as YAML).
- Simulation knobs: symbol, timeframe, start/end (unix seconds), initial capital, optional backtest costs/sizing (defaults from `config.yaml` `backtest` block).
- Reuse Phase 3 pipeline pieces: `get_candles` → `evaluate_signals` / `evaluate_dual_strategy` → `run_backtest` → `compute_metrics` (+ optional buy-and-hold benchmark).
- Persist: strategy snapshot, metrics JSON, equity series, chart `signals` / `trades` markers, full trade rows.
- Extend `GET /chart-data` with optional `runId`; when `includeSignals` / `includeTrades` and run exists, filter markers into the requested window.
- Update OpenAPI (+ Postman if trivial).
- Pytest coverage for happy path, validation, 404, chart-data overlay.
- Optional thin FE on `/backtest` if low risk; otherwise document deferral + client stubs.

### Out of scope / deferred

| Item | Reason |
|---|---|
| Rewrite / fork of `backtest/engine.py` | Explicitly forbidden — wrap CLI engine. |
| Async job queue / progress WS | Sync POST is enough for v1 windows. |
| Workspace / drawings / layout sync | Separate track (was mentioned in 4b as “4d”; not this phase’s roadmap theme). |
| Auth / private runs | D-69 / Phase 11. |
| Live trading / order placement | Out of product vision. |
| Full FE results dashboard (equity chart polish, strategy builder) | Later FE phase; thin page only if low risk. |
| Populating chart-data signals/trades **without** a `runId` | No free-floating signal stream in v1. |
| Replay OverlayPipeline signals/trades | Replay stays indicators-only until a later phase. |

### Current codebase baseline (as of PRD)

- Engine complete under `backend/backtest/` + CLI `run_backtest.py`.
- API has chart-data with **hardcoded empty** `signals` / `trades`.
- No `app.backtest_runs` table; latest migration `V007`.
- FE `BacktestPage` is a placeholder pointing at “Phase 4c”.

---

## 4. UX / API Flows

### 4.1 Run backtest (happy path)

```
Client POST /api/v1/backtest
  { symbol, timeframe, start, end, initialCapital?, strategyName | strategy, backtest? }
  → validate symbol active + timeframe
  → load candles for [start, end]
  → evaluate signals → run_backtest → metrics
  → persist app.backtest_runs
  → 201 { runId, metrics, tradeCount, equityPreview?, … }
```

### 4.2 Inspect run

```
GET /api/v1/backtest/{runId}           → summary + metrics + equity + marker arrays
GET /api/v1/backtest/{runId}/trades    → { runId, trades: [...] }
```

### 4.3 Chart overlay

```
GET /chart-data?...&includeSignals=true&includeTrades=true&runId={uuid}
  → candles + indicators as today
  → signals/trades filtered to [start, end] from persisted run (empty if flags false)
```

### 4.4 Strategy catalog

```
GET /api/v1/backtest/strategies → [{ name, kind: "long_only"|"dual" }, …]
```

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | `POST /backtest` with `strategyName` from catalog runs Phase 3 engine and returns `201` with `runId` + metrics. |
| **AC-2** | Inline `strategy` body works equivalently; both name and inline together → `422`. |
| **AC-3** | Run persisted in `app.backtest_runs`; `GET /backtest/{runId}` returns same metrics/trades. |
| **AC-4** | `GET /backtest/{runId}/trades` returns the full trade log (entry/exit times, prices, side, exit reason, PnL fields). |
| **AC-5** | Unknown `runId` → `404` with error envelope. |
| **AC-6** | No candles in range → `422` with stable code (e..g. `NO_CANDLES`). |
| **AC-7** | Invalid strategy / timeframe / symbol → appropriate `4xx` codes (no 500 for validation). |
| **AC-8** | `GET /chart-data` with `runId` + include flags returns non-empty markers when the run has trades/signals in window; without `runId` still returns `[]`. |
| **AC-9** | Engine modules under `backtest/` are not rewritten; API wraps them. |
| **AC-10** | OpenAPI documents new paths + `runId` on chart-data; pytest green for new + existing API tests. |
| **AC-11** | ROADMAP Phase 4d marked complete with notes; agent reports A–H written. |

---

## 6. Non-functional

- Sync request latency acceptable for typical windows (hours–months of bars); no hard SLA. Document that very large windows may be slow.
- Idempotency: each POST creates a **new** `run_id` (no client idempotency key in v1).
- Timestamps: unix seconds UTC everywhere (match Phase 4).
- JSON field casing: snake on wire for new backtest models unless existing chart-data aliases require camel (`nextStart`, `runId` query alias).

---

## 7. Product defaults (auto-approved)

1. **Sync execution** — no job table / polling in v1.
2. **Named XOR inline strategy** — catalog from `config.yaml`.
3. **chart-data requires `runId`** to populate signals/trades.
4. **Thin FE optional** — prefer backend-complete; ship minimal `/backtest` form if low risk.
5. **Workspace sync out of scope** for this pipeline run.

---

## 8. Done when

All AC-1..AC-11 pass with pytest evidence; OpenAPI updated; ROADMAP Phase 4d status updated; `agent-h-report.md` records final verdict.
