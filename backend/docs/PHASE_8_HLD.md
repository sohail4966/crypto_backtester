# Phase 8 HLD — Screener & Alert Engine

**Status:** Complete (v1)  
**Phase:** Backend Phase 8  
**PRD / design:** [docs/agents/be-phase-8-screener/](../../docs/agents/be-phase-8-screener/)  
**Decisions:** D-102–D-108  
**Prerequisite:** Phase 2 indicators, Phase 3/4d signals + API, Timescale `get_candles()`

---

## 1. Goal

Run a signal condition tree across many symbols and timeframes, fire **edge**
alerts (default) to the console/log, optionally persist scan history — without
leaving TimescaleDB.

Canonical example:

> All coins where RSI(14) &lt; 30 on the daily **and** close &gt; SMA(200)

---

## 2. Architecture

```
run_scan.py --once  /  POST /api/v1/scan
        │
        ▼
  screener.pipeline.run_scan
        │
        ├─ resolve symbols (explicit | active catalog)
        ├─ for each (symbol, timeframe):
        │     get_candles → evaluate condition (± MTF frames)
        │     alert_trigger(edge|level) → last-bar match?
        ├─ AlertSink.log
        └─ app.scan_runs (optional)
```

**D-06 preserved:** all candle IO through `get_candles()`.

---

## 3. Condition DSL (screener slice)

| Key | Meaning |
|---|---|
| `all` | AND of child conditions (existing) |
| `any` | OR of child conditions (**new**) |
| `not` | Unary negation (**new**) |
| leaf | indicator / `smc` / … as today |
| `timeframe` | Optional on leaf; evaluate on that TF, as-of ffill to base |

Alert / scan trigger (D-102):

| Mode | Behavior |
|---|---|
| `edge` (default) | True only when condition becomes true |
| `level` | True on every bar the condition holds |

---

## 4. Scan semantics

1. Load closed candles for the requested window (inclusive ISO/unix range).
2. Evaluate the boolean Series on that window.
3. Apply `alert_trigger`.
4. **Match** if the last bar is True.
5. Emit an alert log line per match.
6. Multi-TF = independent evaluation per `(symbol, timeframe)` unless leaves
   declare a different `timeframe` (then frames map + ffill).

Scheduling (D-103): operators run `run_scan.py --once` after candle close (cron).
No mid-bar / insert-trigger scanner in v1.

---

## 5. Persistence

Table `app.scan_runs` (migration V009): scan metadata, condition JSON, matches
JSONB, `alert_count`, `duration_ms`.

---

## 6. Alert delivery (D-108)

v1 sink: Python `logging` at INFO (`screener.alerts`). Email / webhook / Telegram
deferred.

---

## 7. Deployment (D-104)

Local-first. Cron on a developer machine is the supported always-on pattern until
Phase 11 auth/live.

---

## 8. Performance / storage (D-107)

Stay on Timescale. ClickHouse migration remains a future option if multi-symbol
scans miss the ROADMAP &lt;10s / 50+ symbol target in real workloads.

---

## 9. Completion assessment

| Criterion | Status |
|---|---|
| Multi-symbol + multi-TF scan | Done |
| AND/OR/NOT + optional TF on legs | Done |
| Edge default alerts + console | Done |
| CLI `--once` + optional REST | Done |
| Persist scan_runs | Done |
| Timescale only | Done |
| Tests + ROADMAP | Done |

---

## 10. Non-goals

Full Phase 9 DSL (lookback, sequences), FE UI, cloud auth, email delivery,
ClickHouse.
