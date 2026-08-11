# PRD — BE Phase 8: Screener & Alert Engine

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Backend Phase 8 |
| **Product intent** | [ROADMAP.md — Phase 8](../../../backend/docs/ROADMAP.md#phase-8--screener--alert-engine) |
| **Prior contracts** | `signals/evaluator`; Phase 4d API patterns; OQ-21/22/29 (auto-resolved) |
| **Decisions** | D-102–D-108 |

---

## 1. Problem / Goal

### Problem

Traders need to apply the same signal dict across many symbols and timeframes,
get notified when a condition *becomes* true, and keep a history of matches —
without migrating off TimescaleDB yet.

### Goal

Ship a **screener + alert engine** that:

1. Scans a signal/condition dict across tracked symbols (multi-symbol).
2. Supports multi-timeframe scans (≥2 TFs).
3. Extends the evaluator DSL with nested **AND / OR / NOT** (`all` / `any` / `not`).
4. Fires alerts with **edge** trigger by default (level opt-in).
5. Delivers alerts to **console/log** (email/webhook deferred).
6. Provides cron-friendly `run_scan.py --once` (and optional `POST /scan`).
7. Persists scan result summaries when a run completes.

Success: unit tests lock contracts; a two-TF scan over catalog symbols completes
on Timescale without ClickHouse; ROADMAP Phase 8 marked complete.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Developer / operator** | Runs `run_scan.py --once` via cron or CLI. | Local |
| **API consumer** | Optional `POST /api/v1/scan`. | None (D-69) |
| **Library consumer** | Imports `screener` / uses extended conditions. | N/A |

---

## 3. Scope

### In scope (v1)

| Feature | Notes |
|---|---|
| Multi-symbol scan | Active `app.symbols` (or explicit symbol list) |
| Multi-TF scan | ≥2 timeframes; per `(symbol, timeframe)` evaluation |
| Cross-TF legs | Optional `timeframe` on a condition; as-of ffill to base (no lookahead) |
| AND / OR / NOT | Nested `all` / `any` / `not` in condition trees |
| Alert trigger | Default **edge**; `alert_trigger: level` opt-in (D-102) |
| Alert delivery | `logging` / console sink only |
| CLI | `run_scan.py --once` cron-friendly |
| Persistence | `app.scan_runs` (+ match rows JSONB) |
| REST | `POST /api/v1/scan` (sync, low risk, mirrors backtest) |
| Tests | `tests/screener/`, evaluator AND/OR/MTF, API scan tests |
| Stay on Timescale | No ClickHouse migration (D-107) |

### Out of scope / deferred

| Item | Reason |
|---|---|
| Email / webhook / Telegram | Phase later |
| Full Phase 9 DSL (lookback, sequences) | OQ-25 / Phase 9 |
| ClickHouse migration | Evaluate later if slow |
| Cloud always-on / auth | OQ-29 → local-first (D-104); Phase 11 |
| FE screener UI | Future FE |
| Editing `patterns/` / `smc/` packages | Imports only |

---

## 4. UX / API Flows

### 4.1 CLI

```bash
python run_scan.py --once \
  --timeframes 1h,1d \
  --start 2024-01-01 --end 2024-06-01 \
  --condition-file scan.json
```

### 4.2 Library

```
symbols × timeframes → load candles → evaluate condition → matches + alerts
```

### 4.3 REST

```
POST /api/v1/scan
  { symbols?, timeframes, start, end, condition, alert_trigger?, persist? }
→ { scan_id, matches[], alert_count, duration_ms }
```

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | Multi-symbol scan against active catalog (or explicit list) |
| **AC-2** | Multi-TF (≥2) supported in one run |
| **AC-3** | Nested `all` / `any` / `not` evaluated correctly |
| **AC-4** | Alerts default edge; level configurable; console/log delivery |
| **AC-5** | `run_scan.py --once` exits 0 on success (cron-friendly) |
| **AC-6** | Scan results persist to `app.scan_runs` when requested |
| **AC-7** | `POST /scan` available and tested |
| **AC-8** | OQ-21/22/29 resolved in DECISIONS; no ClickHouse |
| **AC-9** | Tests green; PHASE_8_HLD + ROADMAP updated; A–H artifacts |

---

## 6. Non-goals / constraints

- Do not modify `patterns/` or `smc/` except import usage from screener/evaluator if needed.
- Do not break existing `all`-only AND strategies.
- Closed-candle semantics only (no evaluating incomplete open bars).
