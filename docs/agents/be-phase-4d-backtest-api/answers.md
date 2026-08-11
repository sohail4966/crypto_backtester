# Answers — BE Phase 4d: Backtest HTTP API (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md).

---

### Q1 → Answer

**Sync-only for v1.** `POST /backtest` blocks until the engine finishes and returns `201` with the persisted run. No job table, poll URL, or `202`. Document that very large windows may be slow; clients should choose reasonable ranges. Async can land later if needed.

### Q2 → Answer

**Exactly one of `strategy_name` or `strategy`.** Both or neither → `422` code `INVALID_STRATEGY`. Inline dicts run through the same `_validate_strategy` / D-51 checks as YAML strategies before evaluation.

### Q3 → Answer

**Empty arrays.** `includeSignals` / `includeTrades` true without `runId` still returns `[]` — no 501, no live strategy recompute on chart-data.

### Q4 → Answer

**`404 RUN_NOT_FOUND`** when `runId` is provided but missing. Chart clients that pass a stale id should see a hard error rather than silently empty overlays.

### Q5 → Answer

**Separate entry + exit markers** per round-trip on chart `trades` (tech design §5). Metadata includes `event`, `trade_index`, and exit fields on the exit marker.

### Q6 → Answer

**No disk IO on the HTTP path.** Do not call `save_equity_curve` or `export_trades_csv`. Force `export_trades=False` (or equivalent) when constructing `BacktestConfig` for API runs.

### Q7 → Answer

**Full per-bar equity** aligned to candle timestamps for v1 (`[{time, value}, …]`). Keeps charting simple; revisit downsampling only if payload size becomes a measured problem.

### Q8 → Answer

Chart **`signals` use signal-bar times** (when the evaluator series is True — after edge/level handling). Chart **`trades` use fill times** (`Trade.entry_date` / `exit_date`). This preserves D-14 visibility: signal may appear one bar before the fill marker.

### Q9 → Answer

**Yes — thin `/backtest` page in Agent E scope.** Form + metrics + trades table via new API client. **No** wiring of markers onto the live chart `/` in this phase.

### Q10 → Answer

FE uses **date inputs** (`YYYY-MM-DD`) converted to unix: start = `00:00:00 UTC` of start date; end = `23:59:59 UTC` of end date (or last second of day). API remains unix-seconds native.

### Q11 → Answer

**Workspace / drawings sync is out of scope** for this pipeline. Phase 4d here means backtest HTTP + chart-data markers only (D-95 / roadmap theme).

### Q12 → Answer

**Read-only catalog from `config.yaml`.** `GET /backtest/strategies` lists names; process restart picks up YAML edits. No strategy CRUD/upload in v1 (inline `strategy` body covers ad-hoc runs).

---

## Gate

Auto-approved — proceed to Agent D implementation.
