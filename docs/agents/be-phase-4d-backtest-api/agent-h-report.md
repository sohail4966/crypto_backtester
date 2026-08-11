# Agent H Report — BE Phase 4d: Backtest HTTP API (Final E2E Review)

| Field | Value |
|---|---|
| **Verdict** | **READY_WITH_NITS** |
| **Date** | 2026-08-11 |
| **Inputs** | [prd.md](./prd.md), [tech-design.md](./tech-design.md), [answers.md](./answers.md), [agent-d-report.md](./agent-d-report.md), [agent-e-report.md](./agent-e-report.md), [agent-f-report.md](./agent-f-report.md), [agent-g-report.md](./agent-g-report.md) |
| **Quality gate** | Backend API + backtest pytest green; FE `backtestApi` vitest green; OpenAPI 0.5.0 |

---

## Final verdict

**READY_WITH_NITS** — Phase 4d exposes sync `POST /backtest`, persisted runs, trade log, strategy catalog, and chart-data overlays via `runId`. Phase 3 engine is wrapped, not rewritten. Thin `/backtest` FE page ships. Residual nits: Pydantic XOR 422 envelope shape; no live-chart marker wiring; full-suite has an unrelated `data.yaml` history-depth assertion drift.

---

## AC checklist

| AC | Criterion | Status | Evidence |
|---|---|---|---|
| **AC-1** | POST named strategy → 201 + runId + metrics | **PASS** | Service path + catalog; mocked insert test; strategies list includes `full_stack_confluence` |
| **AC-2** | Inline XOR; both/neither → 422 | **PASS** | `test_post_backtest_xor_*` |
| **AC-3** | Persist + GET run | **PASS** | `BacktestRepository` + `get_backtest` |
| **AC-4** | GET trades detail log | **PASS** | `test_get_backtest_trades` |
| **AC-5** | Unknown runId → 404 | **PASS** | `test_get_backtest_404` |
| **AC-6** | No candles → 422 `NO_CANDLES` | **PASS** | `test_post_backtest_no_candles` |
| **AC-7** | Invalid strategy/TF/symbol → 4xx | **PASS** | ValidationError path + symbol require |
| **AC-8** | chart-data `runId` overlays | **PASS** | `test_chart_data_with_run_id_overlays` / empty without runId / 404 unknown |
| **AC-9** | Engine not rewritten | **PASS** | Imports `run_backtest` / `compute_metrics` only |
| **AC-10** | OpenAPI + pytest | **PASS** | `openapi.yaml` 0.5.0; API suite green |
| **AC-11** | ROADMAP + agent reports | **PASS** | ROADMAP Phase 4d Complete; A–H artifacts |

---

## Test results

### Backend (phase-relevant)

```
pytest tests/api/ tests/backtest/ tests/config/test_backtest_config.py
→ 91 passed
```

Full repo `pytest` also reports **1 failed** unrelated to 4d:
`tests/config/test_data_config.py::test_load_data_config_per_symbol_history_depth`
(expects BTC `8y` / SOL `4y`; current `data.yaml` has `1y` for all). Not introduced by this phase.

### Frontend

```
vitest run src/services/backtestApi.test.ts → 3 passed
tsc -b → clean
```

---

## Docs status updates

| Doc | Change |
|---|---|
| `backend/docs/ROADMAP.md` | Phase 4d **Not started** → **Complete** with deliverable table |
| `backend/docs/openapi.yaml` | Version **0.5.0**; backtest paths; chart-data `runId` |
| `docs/agents/PIPELINE_QUEUE.md` | Mark `be-phase-4d-backtest-api` complete |

---

## Residual risks / nits

1. Sync POST may be slow on very large windows (no async job in v1).
2. Live chart page does not yet pass `runId` into `/chart-data` (API ready).
3. Unrelated `data.yaml` vs test history-depth mismatch in full suite.
4. Manual smoke still recommended: migrate V008 → POST named strategy on synced DB → GET trades → chart-data with `runId`.

---

## Completion notes

Phase 4d closes the deferred chart-data signals/trades contract from Phase 4b by requiring a persisted backtest `runId`. Clients can list strategies, run sync backtests, and render markers once FE chart overlay wiring lands in a later phase.
