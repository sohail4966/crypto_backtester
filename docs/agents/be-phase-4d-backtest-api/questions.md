# Clarifying Questions — BE Phase 4d: Backtest HTTP API

Review of [prd.md](./prd.md) + [tech-design.md](./tech-design.md), cross-checked against Phase 3 engine, Phase 4b deferred notes, and OpenAPI. Questions only — no proposed answers.

---

## Contract / API

### Q1 — Sync vs async

PRD defaults to synchronous `POST /backtest`. Long windows (years of 5m bars) may take many seconds and risk gateway timeouts.

**Question:** Is sync-only final for v1, or should POST enqueue a job and return `202` + poll URL?

### Q2 — Strategy XOR rules

Tech design requires exactly one of `strategy_name` / `strategy`.

**Question:** Confirm both present or both absent → `422` with code `INVALID_STRATEGY`, and that inline strategies must pass the same `_validate_strategy` rules as YAML (including D-51 risk_pct + stop_loss)?

### Q3 — chart-data without runId

**Question:** When `includeSignals`/`includeTrades` are true but `runId` is omitted, confirm response remains empty arrays (not 501 / not live recompute)?

### Q4 — Unknown runId on chart-data

**Question:** Unknown `runId` → `404 RUN_NOT_FOUND`, or treat as empty markers to keep chart loading resilient?

### Q5 — Trade marker cardinality

**Question:** Should chart `trades` be one marker per round-trip (entry time only), or separate entry + exit markers (tech design §5)?

---

## Persistence / engine

### Q6 — Disk side effects

CLI writes equity PNG and trades CSV. API path must avoid that.

**Question:** Confirm API never calls `save_equity_curve` / `export_trades_csv`, and `BacktestConfig.export_trades` is forced false on the HTTP path?

### Q7 — Equity series length

**Question:** Persist full per-bar equity aligned to candles, or downsample (e.g. daily) for JSONB size?

### Q8 — Signal series source

Evaluator returns boolean Series (possibly edge-triggered). Engine fills next bar.

**Question:** Should chart `signals` use **signal bar times** (when condition fired) or **fill bar times** (when trade opened/closed)?

---

## Frontend

### Q9 — Agent E scope

**Question:** Confirm thin `/backtest` page (form + metrics + trade table) is in scope, with **no** live-chart marker wiring on `/` in this phase?

### Q10 — Date inputs

**Question:** FE form uses date-only inputs converted to unix start-of-day / end-of-day UTC, or raw unix seconds fields?

---

## Scope boundaries

### Q11 — Workspace sync

Phase 4b text also parked workspace sync under “4d”. Roadmap Phase 4d theme is backtest HTTP only.

**Question:** Confirm workspace/drawings sync is **out of scope** for this pipeline run?

### Q12 — Config catalog mutability

**Question:** Is the strategy catalog read-only from `config.yaml` (restart to pick up changes), or must we support upload/CRUD of strategies in v1?
