# Phase 4b — Frontend Integration Gaps (Backend Fixes)

**Status:** Open — discovered during [FE Phase 1](../../frontend/docs/FE_PHASE_1_HLD.md)  
**Prerequisite:** [PHASE_4B_HLD.md](PHASE_4B_HLD.md) shipped (API v0.4.1)  
**Blocks removing:** Frontend workarounds in `resolveCandleDataRange`, sentinel windows, 1m anchor fallback  
**Target:** Small backend patch (no new endpoints required) — call it **Phase 4b.1** or fold into 4c prep

---

## Why This Doc Exists

Phase 4b exposed `GET /chart-data` and `GET /symbols/{id}/data-range` for the chart client.
During FE Phase 1 smoke testing, the **happy path works for `1m`** but **derived timeframes**
(`1h`, `4h`, `1d`, …) break metadata and fallback paths even though aggregated candles
are returned when the client sends a valid window.

The frontend added workarounds; this document records what the **backend must fix** so
the client can stay dumb: *call API → render candles*.

---

## Architecture Context

| Layer | Behaviour today |
|---|---|
| Storage | Only **`1m`** rows are persisted in `candles` (Phase 1 design) |
| Reads | Higher timeframes are **derived on read** via `time_bucket` SQL ([`SELECT_DERIVED_CANDLES_BY_RANGE`](../data/repository/queries.py)) |
| Metadata | `latest_timestamp`, `earliest_timestamp`, `bar_count` query `WHERE timeframe = %s` on **raw rows** |
| Gap | Metadata queries use `timeframe='1h'` but no `1h` rows exist → **null / 0** |

```
┌─────────────────────────────────────────────────────────────────┐
│  candles table (timeframe = '1m' only)                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
  find_derived_by_date_range                   latest_timestamp('1h')
  (aggregation SQL — WORKS)                    (SELECT MAX … tf='1h' — FAILS)
```

---

## Gap 1 — `data-range` Returns Empty for Derived Timeframes

**Endpoint:** `GET /api/v1/symbols/{symbol}/data-range?timeframe=`

**Observed (BTC/USDT, synced DB):**

```bash
# 1m — correct
curl '/api/v1/symbols/BTC%2FUSDT/data-range?timeframe=1m'
# → earliest, latest, barCount populated

# 1h — wrong
curl '/api/v1/symbols/BTC%2FUSDT/data-range?timeframe=1h'
# → {"earliest":null,"latest":null,"barCount":0}
```

**Root cause:** [`CandleService.get_data_range`](../api/services/candle_service.py) calls
[`CandleRepository.latest_timestamp` / `earliest_timestamp` / `bar_count`](../data/repository/candle_repository.py)
with the requested timeframe. Those methods run `SELECT MAX/MIN/COUNT … timeframe = %s`
against stored rows only.

**Impact:** Frontend cannot anchor chart windows on `latest` for `1h+` without a 1m fallback.

**Fix:**

| File | Change |
|---|---|
| `data/repository/queries.py` | Add `SELECT_DERIVED_MAX_TS`, `SELECT_DERIVED_MIN_TS`, `SELECT_DERIVED_BAR_COUNT` using the same `time_bucket` aggregation as `SELECT_DERIVED_CANDLES_BY_RANGE` |
| `data/repository/candle_repository.py` | Branch: `timeframe == '1m'` → existing queries; else → derived metadata queries |
| `api/services/candle_service.py` | `get_data_range` uses derived-aware repository methods |
| `tests/api/test_symbol_data_range.py` | Integration test with mocked derived aggregation **or** fixture DB with 1m rows asserting non-null `1h` range |

**Done when:** `data-range?timeframe=1h` returns non-null `latest` whenever `1m` data exists.

---

## Gap 2 — `get_latest_candles` Fallback Fails for Derived Timeframes

**Path:** `ChartDataService.get_chart_data` → empty window → [`get_latest_candles`](../api/services/candle_service.py)

**Observed:**

```bash
curl '/api/v1/chart-data?symbolId=BTC%2FUSDT&timeframe=1h&start=0&end=1&limit=500'
# → candles: []   (fallback did not load latest bars)

curl '/api/v1/chart-data?symbolId=BTC%2FUSDT&timeframe=1h&start=<anchored>&end=<1m-latest>&limit=500'
# → candles: 500  (valid window anchored on 1m latest works)
```

**Root cause:** `get_latest_candles` calls `latest_timestamp(symbol, timeframe)` which
returns `None` for derived timeframes (Gap 1). Fallback exits early with empty bars.

**Fix:** After Gap 1 repository methods exist:

```python
latest = self._candle_repository.latest_timestamp(symbol, timeframe, conn=conn)
# derived path now returns aligned bucket of MAX(1m)
```

Optionally align `latest` down to the last **closed** bucket open time for the requested timeframe.

**Done when:** `chart-data` with an empty/non-overlapping window returns up to `limit` latest
bars for `1h` the same way it does for `1m`.

---

## Gap 3 — `get_candles` Returns Oldest Bars When Range Is Wide

**Not a blocker for FE Phase 1** (window is now anchored on `latest`), but affects API ergonomics.

When `len(bars) > limit`, [`CandleService.get_candles`](../api/services/candle_service.py) truncates
with `bars[:effective_limit]` — the **first** bars in the range, not the **most recent**.

**Impact:** Clients that pass a wide historical window without a tight `end` anchor get ancient
data instead of the latest N bars.

**Fix options (pick one):**

| Option | Description |
|---|---|
| A | When `len(bars) > limit`, keep `bars[-effective_limit:]` (tail slice) |
| B | Document that clients must anchor `end` on `data-range.latest` (status quo + Gap 1 fix) |
| C | Add `order=desc` query param on chart-data (heavier change) |

**Recommendation:** **A** for `get_latest_candles` internal path; keep ascending order in
response. For explicit historical windows, current head-slice behaviour may still be desired —
consider tail-slice only inside `get_latest_candles` / empty-window fallback.

---

## Gap 4 — Optional: `latest` Query Param on `chart-data`

**Priority:** Low — fixes above may make this unnecessary.

A simpler client contract:

```
GET /chart-data?symbolId=BTC/USDT&timeframe=1h&limit=500
# No start/end required — server returns latest 500 bars
```

**Scope:** New optional parameters on [`chart_data.py`](../api/routers/chart_data.py);
when `start`/`end` omitted, resolve window from derived metadata. OpenAPI + tests.

Defer unless product wants zero-window chart loads.

---

## Frontend Workarounds Today (Remove After Backend Fix)

| FE file | Workaround |
|---|---|
| [`chartDataAdapter.ts`](../../frontend/src/services/chartDataAdapter.ts) | `resolveCandleDataRange()` — fetches `1m` data-range when derived `latest` is null |
| [`useChunkManager.ts`](../../frontend/src/hooks/useChunkManager.ts) | `initialChartDataQueryKey` — stable React Query cache per symbol+timeframe |
| [`QueryProvider.tsx`](../../frontend/src/app/QueryProvider.tsx) | `refetchOnMount: false` — avoids duplicate calls on route remount |

After Gaps 1–2 are fixed, FE can call `getCandleDataRange` directly and delete
`resolveCandleDataRange`.

---

## Implementation Checklist

- [ ] Derived metadata SQL in `queries.py`
- [ ] Repository branches for `1m` vs derived in `latest_timestamp`, `earliest_timestamp`, `bar_count`
- [ ] `get_data_range` returns correct bounds for `1h`, `4h`, `1d`
- [ ] `get_latest_candles` returns bars for derived timeframes
- [ ] `chart-data` empty-window integration test for `1h` (extend [`test_chart_data.py`](../tests/api/test_chart_data.py))
- [ ] `data-range` integration test for `1h` with 1m fixture data
- [ ] OpenAPI description note: derived timeframes aggregated from stored `1m`
- [ ] Postman folder updated if examples change

---

## Verification Commands

```bash
# After fix — both should return non-empty candles without client-side anchoring hacks
curl 'http://localhost:8000/api/v1/symbols/BTC%2FUSDT/data-range?timeframe=1h'

curl 'http://localhost:8000/api/v1/chart-data?symbolId=BTC%2FUSDT&timeframe=1h&start=0&end=1&limit=500'
```

---

## Relationship to Other Phases

```
Phase 4b (shipped) ──► Phase 4b.1 (this doc) ──► remove FE workarounds
        │
        ├── Phase 4c — Replay V2 (WebSocket streaming)
        ├── Phase 4d — backtest HTTP, signals/trades in chart-data
        ├── Phase 4d — workspace sync
        └── Phase 5 — market structure (parallel)
```

---

## References

- [PHASE_4B_HLD.md](PHASE_4B_HLD.md)
- [PHASE_1_HLD.md](PHASE_1_HLD.md) — canonical 1m storage, derived reads
- [FE_PHASE_1_HLD.md](../../frontend/docs/FE_PHASE_1_HLD.md)
- [SPEC-001 §7.1](../../frontend/docs/SPEC-001.md)
- [openapi.yaml](openapi.yaml)
