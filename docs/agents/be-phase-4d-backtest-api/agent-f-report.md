# Agent F Report — Review of Agent D (Backend)

| Field | Value |
|---|---|
| **Role** | Review / harden D |
| **Verdict** | **PASS_WITH_NITS** |
| **Date** | 2026-08-11 |

---

## Findings

| Severity | Finding | Resolution |
|---|---|---|
| Important | Unknown `runId` on chart-data needed explicit coverage | Added `test_chart_data_unknown_run_id_404` |
| Nit | Body XOR validation uses FastAPI/Pydantic 422 envelope (not `{"error":…}`) | Acceptable for request schema; service-level errors use API envelope |
| Nit | Full per-bar equity JSONB may grow large on multi-year 1m windows | Documented in design; revisit if measured |

## Checks

- Engine modules under `backtest/` untouched (wrap-only) — **PASS**
- `export_trades` forced false on API path — **PASS**
- Route order: `/strategies` before `/{run_id}` — **PASS**
- OpenAPI 0.5.0 + paths present — **PASS**

## Test evidence

`pytest tests/api/` → **61 passed** (after 404 test)
