# Answers — BE Phase 8: Screener & Alert Engine (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into
[tech-design.md](./tech-design.md) and [PHASE_8_HLD.md](../../../backend/docs/PHASE_8_HLD.md).

---

### Q1 → Answer

**Yes.** Alerts default to **edge**; `alert_trigger: level` opts into every-bar-true
firing. Resolves remaining OQ-21 for screener/alerts (**D-102**). Exit-leg
configurability for backtests remains unchanged (still level).

### Q2 → Answer

**Closed candles only.** Evaluators never intentionally use an incomplete open bar.
Scheduling = operator cron/`run_scan.py --once` after the relevant TF close (UTC).
No DB-insert trigger in v1 (**D-103** / OQ-22).

### Q3 → Answer

**Local-first** through Phase 8. Cloud always-on and auth stay Phase 11 (**D-104** /
OQ-29).

### Q4 → Answer

**Nested Option A:** extend with `any` (OR) and `not` (unary); keep existing `all`
(AND). Document as Phase 8 screener DSL slice; full Phase 9 grammar later (**D-105**).

### Q5 → Answer

**Yes.** Optional `timeframe` on leaf conditions. Other-TF series are aligned to the
base candle index via as-of **ffill** (same no-lookahead spirit as D-58) (**D-106**).

### Q6 → Answer

**Out of scope.** OQ-25 remains open for Phase 9.

### Q7 → Answer

**Yes — cartesian** `(symbol × timeframe)` with the same condition tree. Cross-TF
legs inside one tree are additive via `timeframe` on leaves when a base TF + frames
map is provided.

### Q8 → Answer

**Yes.** Default = active `app.symbols`; explicit list overrides.

### Q9 → Answer

**Yes.** Match = True on the last closed bar after applying `alert_trigger`
(edge/level) to the level boolean Series.

### Q10 → Answer

**Console / logging only.** Email/webhook deferred (**D-108**).

### Q11 → Answer

**Yes.** `app.scan_runs` with condition + matches JSONB. CLI persists by default;
API `persist` defaults true.

### Q12 → Answer

**Yes.** Sync `POST /api/v1/scan` (low risk, backtest-shaped).

### Q13 → Answer

**Stay on Timescale.** No ClickHouse in Phase 8 (**D-107**). Revisit if scans miss
the &lt;10s / 50-symbol goal in production.

### Q14 → Answer

**Yes.** Own `screener/`, evaluator/`signals.types`, API, migration, CLI, docs,
tests. Do not edit `patterns/**` or `smc/**` bodies (imports OK).

---

## Gate

Auto-approved — proceed to Agent C tech design / Agent D implementation.
