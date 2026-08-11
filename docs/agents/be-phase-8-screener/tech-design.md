# Tech Design — BE Phase 8: Screener & Alert Engine

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **Decisions** | D-102–D-108 |
| **HLD** | [PHASE_8_HLD.md](../../../backend/docs/PHASE_8_HLD.md) |
| **Agent D** | `screener/` + evaluator AND/OR/NOT/MTF + CLI + migration + tests |
| **Agent E** | `POST /api/v1/scan` + OpenAPI |
| **Answers** | [answers.md](./answers.md) |

---

## 1. Architecture Overview

```
CLI run_scan.py --once          POST /api/v1/scan
            │                         │
            └────────────┬────────────┘
                         ▼
              ┌─────────────────────┐
              │ ScreenerService /   │
              │ screener.pipeline   │
              └──────────┬──────────┘
                         │
         symbols × timeframes
                         │
                         ▼
              get_candles (D-06) ──► evaluate_condition
                         │              (+ all/any/not, timeframe)
                         ▼
              last-bar match + alert_trigger (edge|level)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         AlertSink (log)      app.scan_runs (optional)
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **`screener/`** | Scan orchestration, match rows, alerts, MTF frame helpers | Indicator math, HTTP |
| **`signals/evaluator`** | `all` / `any` / `not`, optional `timeframe` + frames map | Symbol catalog, persistence |
| **API** | Validation, persist, response mapping | Scan math |
| **CLI** | Argparse, logging, exit codes | FastAPI |

---

## 2. Package layout

```
backend/
  screener/
    __init__.py
    types.py          # ScanRequest, ScanMatch, ScanResult, AlertEvent
    align.py          # as-of ffill boolean/float Series onto base index
    evaluate.py       # evaluate_scan_condition(candles, condition, frames?)
    scan.py           # run_multi_symbol_scan(...)
    alerts.py         # apply trigger + ConsoleAlertSink
    pipeline.py       # high-level run_scan
  run_scan.py
  data/migrations/sql/V009__scan_runs.sql
  api/
    routers/scan.py
    schemas/scan.py
    services/scan_service.py
    repositories/scan_repository.py
  tests/screener/
  tests/api/test_scan.py
  docs/PHASE_8_HLD.md
```

### Touch outside package

- `signals/types.py` — `any`, `not`, `timeframe` on `SignalCondition`
- `signals/evaluator.py` — `any` / `not` branches; optional `frames` + `base_index` for MTF
- `api/main.py` — mount scan router
- `api/repositories/queries.py` — INSERT/SELECT scan_runs
- `docs/DECISIONS.md`, `OPEN_QUESTIONS.md`, `ROADMAP.md`, `openapi.yaml`
- `docs/agents/PIPELINE_QUEUE.md`

### Do not modify

- `patterns/**` (except imports if ever needed — prefer none)
- `smc/**` (except imports if ever needed — prefer none)
- ClickHouse / loader SQL redesign

---

## 3. DSL extensions (D-105 / D-106)

```json
{
  "all": [
    {"indicator": "RSI", "params": {"period": 14}, "op": "<", "value": 30, "timeframe": "1d"},
    {
      "any": [
        {"indicator": "SMA", "params": {"period": 200}, "op": "price_above"},
        {"not": {"indicator": "RSI", "params": {"period": 14}, "op": ">", "value": 70}}
      ]
    }
  ]
}
```

Notes:

- `price_above` / `price_below` already expressed via `compare: "close"` + op elsewhere;
  v1 keeps existing ops (`<`, `>`, …, `compare`).
- `SMA` “price above” = `{"indicator":"SMA","params":{"period":200},"op":">","compare":"close"}`
  or keep compare semantics as today (`series op compare`).
- Existing `all` behavior unchanged.

### Evaluator signature (additive)

```python
def _evaluate_condition(
    candles: pd.DataFrame,
    condition: SignalCondition,
    *,
    frames: Mapping[str, pd.DataFrame] | None = None,
) -> pd.Series:
    ...
```

When `condition["timeframe"]` is set and `frames` contains that TF, evaluate the leaf
on that frame, then `align.asof_ffill` onto `candles["ts"]`.

---

## 4. Alert semantics (D-102 / D-108)

```python
level = evaluate(...)
triggered = apply_entry_trigger(level, alert_trigger)  # reuse edge_trigger
# Match if triggered.iloc[-1] is True on last closed bar
sink.emit(AlertEvent(...))  # logging.info
```

---

## 5. Database — `V009__scan_runs.sql`

```sql
CREATE TABLE IF NOT EXISTS app.scan_runs (
    scan_id          UUID PRIMARY KEY,
    timeframes       TEXT[]           NOT NULL,
    symbols          TEXT[]           NOT NULL,
    start_ts         BIGINT           NOT NULL,
    end_ts           BIGINT           NOT NULL,
    condition_config JSONB            NOT NULL,
    alert_trigger    TEXT             NOT NULL DEFAULT 'edge',
    matches          JSONB            NOT NULL DEFAULT '[]',
    alert_count      INT              NOT NULL DEFAULT 0,
    duration_ms      INT              NOT NULL DEFAULT 0,
    status           TEXT             NOT NULL DEFAULT 'completed',
    error_message    TEXT,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_runs_created
  ON app.scan_runs (created_at DESC);
```

---

## 6. REST — `POST /api/v1/scan`

Request:

```json
{
  "timeframes": ["1h", "1d"],
  "start": 1704067200,
  "end": 1717200000,
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "condition": { "all": [ ... ] },
  "alert_trigger": "edge",
  "persist": true
}
```

If `symbols` omitted → active catalog. Response includes `scan_id`, `matches`,
`alert_count`, `duration_ms`.

---

## 7. CLI — `run_scan.py`

| Flag | Meaning |
|---|---|
| `--once` | Required for cron mode (exit after one scan) |
| `--timeframes` | Comma list, ≥1 (recommend ≥2) |
| `--start` / `--end` | ISO dates |
| `--symbols` | Optional comma list |
| `--condition-file` | JSON condition |
| `--alert-trigger` | `edge` \| `level` |
| `--no-persist` | Skip DB write |

---

## 8. Testing plan

| Area | Tests |
|---|---|
| Evaluator | `any`, `not`, nested mix; MTF ffill no lookahead |
| Screener | Multi-symbol mock candles; multi-TF; edge vs level last-bar |
| Alerts | Console sink called on edge |
| API | POST validation + mocked scan persist |
| CLI | `--once` argparse smoke (optional light) |

---

## 9. Agent split

| Agent | Work |
|---|---|
| **D** | Library + evaluator + migration + CLI + unit tests + HLD/ROADMAP/decisions |
| **E** | Router/schemas/service/repo + OpenAPI + `tests/api/test_scan.py` |
| **F/G** | Spec + quality review reports |
| **H** | Final verdict + pytest summary |

### Coexistence note

Phase 9 DSL work may land in parallel on `signals/evaluator.py`. Phase 8 adds
`any`/`not` key aliases and `evaluate_condition`; Phase 9 `op`/`conditions` groups
remain valid. Prefer not rewriting evaluator leaves owned by Phase 9.
