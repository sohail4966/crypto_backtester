# Clarifying Questions — BE Phase 8: Screener & Alert Engine

Review of [prd.md](./prd.md), ROADMAP Phase 8, OQ-21/22/29, signals evaluator,
Phase 4d API. Questions only — no proposed answers.

---

## Triggers & timing

### Q1 — Alert edge vs level (OQ-21)

**Question:** Confirm screener/alert default is **edge** (fire when condition becomes
true), with `alert_trigger: level` opt-in — aligning with D-52 entry semantics?

### Q2 — Scan timing (OQ-22)

**Question:** Confirm scans evaluate **closed candles only** (last fully closed bar
in range), and scheduled/cron runs use `run_scan.py --once` after expected TF close
rather than DB insert triggers?

### Q3 — Deployment (OQ-29)

**Question:** Confirm **local-first** (developer machine + cron); no cloud always-on
or auth in Phase 8?

---

## DSL

### Q4 — AND/OR/NOT schema (OQ-23 partial)

**Question:** Prefer nested Option A: `{"all":[...]}`, `{"any":[...]}`,
`{"not": {...}}` extending existing `all`?

### Q5 — Multi-TF condition syntax (OQ-24 partial)

**Question:** Allow optional `timeframe` on a leaf condition; when present and
different from the scan base TF, evaluate on that TF’s candles and **as-of
forward-fill** onto the base index (no lookahead)?

### Q6 — Lookback (OQ-25)

**Question:** Confirm lookback / `bars_ago` is **out of scope** for Phase 8 (Phase 9)?

---

## Scan semantics

### Q7 — Multi-TF scan shape

**Question:** Confirm default multi-TF scan is cartesian: evaluate the same
condition independently on each `(symbol, timeframe)`, emitting one match row per
pair that is true on the last closed bar?

### Q8 — Symbol universe

**Question:** Default symbols = active rows in `app.symbols`; request/CLI may pass
an explicit list?

### Q9 — Match bar

**Question:** A symbol×TF “matches” when the evaluated boolean Series is True on
the **last closed bar** in the loaded window (after applying alert_trigger mode)?

---

## Delivery / persistence / API

### Q10 — Alert delivery

**Question:** Confirm console/`logging` only; email/webhook deferred?

### Q11 — Persistence

**Question:** Persist each run to `app.scan_runs` (condition JSON, matches JSONB,
timing) when `persist=true` (API) / default-on for CLI?

### Q12 — REST

**Question:** Include synchronous `POST /api/v1/scan` mirroring backtest style?

### Q13 — ClickHouse

**Question:** Confirm **stay on Timescale**; no migration in this phase?

### Q14 — Package boundaries

**Question:** Own `screener/` + evaluator/types extensions + API/CLI/docs/tests;
do not edit `patterns/` or `smc/` packages (imports OK)?
