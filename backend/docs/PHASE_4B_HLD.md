# Phase 4b High Level Design — Frontend-Ready API Extensions

**Status:** Complete — implementation shipped (API v0.4.1)  
**Prerequisite:** Phase 4 complete ([PHASE_4_HLD.md](PHASE_4_HLD.md))  
**Enables:** [SPEC-001](../../frontend/docs/SPEC-001.md) FE Phases 1–4 (chart, indicators, replay)  
**Decisions:** D-80, D-81, D-82 (FE), D-86, D-87 (FE) in [DECISIONS.md](DECISIONS.md)  
**Next after this:** [Phase 4c](PHASE_4C_HLD.md) (Replay V2) **or** Phase 5 (market structure) in parallel with FE; **Phase 4d** (backtest + trades API)

---

## Why Phase 4b Exists

Phase 4 delivered a working chart API, but the **frontend spec (SPEC-001)** and locked
architecture decisions (D-80–D-87) require contracts Phase 4 does not expose:

| Frontend need (SPEC-001) | Phase 4 today | Phase 4b delivers |
|---|---|---|
| Single chart payload (candles + indicators + signals + trades) | Separate `/candles` + `/indicators/compute` | **`GET /chart-data`** (D-81) |
| Structured `Symbol` (`id`, exchange, tick/lot size) | `symbol`, `base`, `quote` only | **Extended `app.symbols` + v2 response** (D-86) |
| REST replay chunks; FE owns playback | WebSocket step-by-step (D-71) | **`GET /replay/{run_id}/chunk`** (D-80) |
| Symbol search path | `GET /symbols?q=` | **Alias `/symbols/search`** (compat) |

Phase 4b is a **thin extension** — no new compute logic, no auth, no workspace sync
(that is **Phase 4d**). Backtest HTTP and trade payloads in chart-data are **Phase 4c**;
4b returns **empty `signals` and `trades` arrays** when those flags are set until 4c lands.

---

## Phase 4b Goal

Extend the Phase 4 API so the TradingView-style frontend can:

1. **Fetch unified chart windows** in one request (aligned timestamps).
2. **Resolve symbols** as structured entities with stable IDs and trading metadata.
3. **Buffer replay data** via REST chunks while controlling play/pause locally (no replay WS in FE MVP).

**Explicitly in scope**

- `ChartDataService` bundling existing `CandleService` + `IndicatorService`
- `GET /api/v1/chart-data`
- Symbol schema migration `V006` + v2 `SymbolResponse` (backward-compatible field additions)
- `GET /api/v1/symbols/search` alias
- `POST /api/v1/replay/runs` + `GET /api/v1/replay/{run_id}/chunk` + `GET /api/v1/replay/{run_id}/trades` (empty trades until 4c)
- Tests, OpenAPI update, Postman folder

**Explicitly out of scope (unchanged deferrals)**

| Feature | Target phase |
|---|---|
| Workspace / drawings / layout sync | **Phase 4d** (D-85) |
| `POST /backtest`, persisted `run_id` from backtest engine | **Phase 4c** |
| Non-empty `signals` / `trades` in chart-data | **Phase 4c** |
| JWT auth, live candle WebSocket | **Phase 11** (D-78) |
| Replay session DB persistence | **Phase 11** |
| Frontend React app | FE Phase 1+ (parallel once 4b chart-data ships) |
| Market structure | **Phase 5** |

**Backward compatibility:** All Phase 4 endpoints remain. Replay WebSocket (`/ws/replay/{session_id}`) stays for non-FE clients; frontend MVP uses REST chunks only (D-80).

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Frontend (SPEC-001)                                 │
│  useChartData ──► GET /chart-data          replayStore ──► GET /chunk   │
│  chunkManager ◄── ChartDataResponse        (no replay WebSocket)        │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ REST
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Phase 4b additions                                 │
│  routers/chart_data.py    routers/replay.py (+ chunk routes)            │
│  services/chart_data_service.py  (new)                                  │
│  schemas/chart_data.py    schemas/symbols.py (v2)                       │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ reuses
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Phase 4 (unchanged core)                           │
│  CandleService ──► get_candles()     IndicatorService ──► registry      │
│  ReplayService (in-memory sessions)                                     │
└───────────────────────────────┬────────────────────────────────────────┘
                                ▼
                    TimescaleDB + app.symbols (V006)
```

### Layering (new / modified files)

```
api/
  routers/
    chart_data.py          # NEW — GET /chart-data
    replay.py              # EXTEND — /runs, /{run_id}/chunk, /{run_id}/trades
    symbols.py             # EXTEND — GET /symbols/search alias
  schemas/
    chart_data.py          # NEW — ChartDataResponse, Signal, Trade stubs
    symbols.py             # EXTEND — SymbolV2Response (or extend SymbolResponse)
    replay.py              # EXTEND — ReplayRunCreate, ReplayChunkResponse
  services/
    chart_data_service.py  # NEW — bundle candles + indicators (+ empty signals/trades)
    symbol_service.py      # EXTEND — map DB row → structured symbol
    replay_service.py      # EXTEND — get_chunk(run_id, from, limit)
  repositories/
    symbol_repository.py   # EXTEND — read new columns
data/migrations/sql/
  V006__symbol_metadata.sql
tests/api/
  test_chart_data.py       # NEW
  test_replay_chunks.py    # NEW
  test_symbols_v2.py       # NEW
```

### Principles (carried forward)

| ID | Rule | Phase 4b application |
|---|---|---|
| D-06 | `get_candles()` only | `ChartDataService` calls `CandleService`, never raw SQL |
| D-07 / D-72 | Server-side indicators | Bundled in chart-data via `IndicatorService` |
| D-69 | No auth | All new routes public |
| D-70 | Unix seconds | All `time` fields unchanged |
| D-79 | Candle limits | chart-data `limit` default **500**, max **5000** (aligns with FE chunk size D-82) |
| D-80 | REST replay chunks | New chunk routes; WS not required for FE |
| D-81 | Unified response | Single `ChartDataResponse` schema |

---

## Data Model

### Migration: `V006__symbol_metadata.sql`

Extend `app.symbols` for structured symbol entities (D-86). **PK remains `symbol`** —
the API exposes it as `id` for frontend stability.

| Column | Type | Default | Notes |
|---|---|---|---|
| `exchange` | TEXT NOT NULL | `'binance'` | Data source exchange |
| `tick_size` | NUMERIC NOT NULL | per-row seed | Min price increment |
| `lot_size` | NUMERIC NOT NULL | per-row seed | Min quantity increment |
| `asset_type` | TEXT NOT NULL | `'spot'` | `spot` \| `perp` \| `futures` |

**Seed updates (BTC/ETH/SOL spot):**

| symbol | tick_size | lot_size |
|---|---|---|
| BTC/USDT | 0.01 | 0.00001 |
| ETH/USDT | 0.01 | 0.0001 |
| SOL/USDT | 0.01 | 0.01 |

`watchlist_symbols.symbol` FK unchanged (still references `symbol` text PK).

### Replay runs — still in-memory (D-71)

`run_id` is a **UUID** identifying an in-memory replay run. Phase 4b introduces the
**frontend-facing name** `run_id`; it equals the existing `session_id` internally.

```
POST /replay/runs  →  creates ReplaySession  →  returns { run_id, symbol, timeframe, start, end }
GET  /replay/{run_id}/chunk  →  slice of preloaded bars + prefix indicators
GET  /replay/{run_id}/trades →  [] until Phase 4c
```

Phase 4d will add `app.backtest_runs` and allow `run_id` to reference a persisted backtest;
4b document that **historical replay runs** use the in-memory path above.

---

## API Specification

Base: **`/api/v1`**. Public, JSON, unix-second timestamps.

### `GET /chart-data`

Unified chart window (D-81). Replaces the need for parallel `/candles` + `/indicators/compute`
calls for the same view.

**Query parameters**

| Param | Required | Default | Notes |
|---|---|---|---|
| `symbolId` | yes | — | Stable symbol id (= `app.symbols.symbol`, e.g. `BTC/USDT`) |
| `timeframe` | yes | — | `1h`, `4h`, … |
| `start` | yes | — | Inclusive unix seconds |
| `end` | yes | — | Inclusive unix seconds |
| `indicators` | no | `[]` | URL-encoded JSON array of `IndicatorSpec` objects |
| `includeSignals` | no | `false` | **4b:** always returns `[]` (4c populates) |
| `includeTrades` | no | `false` | **4b:** always returns `[]` (4c populates) |
| `limit` | no | **500** | Max bars; max **5000** (D-79) |

**Example**

```
GET /api/v1/chart-data?symbolId=BTC%2FUSDT&timeframe=1h&start=1704067200&end=1706745600
  &indicators=%5B%7B%22key%22%3A%22EMA%22%2C%22params%22%3A%7B%22period%22%3A20%7D%7D%5D
  &includeSignals=false&includeTrades=false&limit=500
```

**Response: `ChartDataResponse`**

```json
{
  "symbol": {
    "id": "BTC/USDT",
    "ticker": "BTC/USDT",
    "exchange": "binance",
    "baseAsset": "BTC",
    "quoteAsset": "USDT",
    "tickSize": 0.01,
    "lotSize": 0.00001,
    "type": "spot",
    "active": true
  },
  "timeframe": "1h",
  "start": 1704067200,
  "end": 1706745600,
  "candles": [
    { "time": 1704067200, "open": 42000, "high": 42500, "low": 41800, "close": 42200, "volume": 1200.5 }
  ],
  "indicators": {
    "EMA_20": [
      { "time": 1704067200, "value": 42100.5 }
    ]
  },
  "signals": [],
  "trades": [],
  "nextStart": 1704153600
}
```

**Field notes**

- `candles`: same shape as Phase 4 `Bar`.
- `indicators`: map keyed by **client-stable id** — `{key}_{param_hash}` or explicit
  `id` field in `IndicatorSpec` if provided; default key = registry `key` + serialized params.
- `signals` / `trades`: empty arrays in 4b when flags false; when true but 4c not shipped,
  return `[]` (not 501).
- `nextStart`: present when more bars exist beyond `limit` (pagination for chunk manager).

**Errors**

| Code | HTTP | When |
|---|---|---|
| `SYMBOL_NOT_FOUND` | 404 | Unknown or inactive symbol |
| `INVALID_TIMEFRAME` | 400 | Unsupported TF |
| `INVALID_RANGE` | 400 | `start > end` |
| `INVALID_INDICATOR` | 400 | Unknown registry key |
| `LIMIT_EXCEEDED` | 400 | `limit > 5000` |

### `ChartDataService` algorithm

```python
def get_chart_data(conn, request: ChartDataRequest) -> ChartDataResponse:
    # 1. Validate symbol + timeframe + range + limit
    # 2. candles = CandleService.get_candles(conn, ..., limit=request.limit)
    # 3. if request.indicators:
    #       series = IndicatorService.compute(conn, symbol, tf, start, end, indicators)
    #    else:
    #       series = {}
    # 4. Align indicator points to candle times (drop outside window; warmup nulls ok)
    # 5. signals = []  # Phase 4c
    # 6. trades = [] if not include_trades else []  # Phase 4c
    # 7. symbol = SymbolService.get_structured(conn, symbolId)
    # 8. return ChartDataResponse(...)
```

Indicator warmup: reuse existing `IndicatorService` + `indicators/warmup.py` behaviour
so the visible window is not all-null at the left edge.

**Performance:** One DB candle load + one indicator compute pass per request. Same cost
as two Phase 4 calls today; fewer HTTP round-trips for the client.

---

### Symbols v2

**Extended `SymbolResponse`** (all list/get/search endpoints return v2 shape):

```json
{
  "id": "BTC/USDT",
  "ticker": "BTC/USDT",
  "exchange": "binance",
  "baseAsset": "BTC",
  "quoteAsset": "USDT",
  "tickSize": 0.01,
  "lotSize": 0.00001,
  "type": "spot",
  "active": true,
  "sortOrder": 1
}
```

**Backward compatibility:** Phase 4 fields `symbol`, `base`, `quote`, `is_active`, `sort_order`
may remain as **deprecated aliases** in OpenAPI for one release, or v2 replaces flat fields
(document breaking change for any early FE adapter — acceptable pre-FE-ship).

| Method | Path | Notes |
|---|---|---|
| GET | `/symbols` | Unchanged query (`q`, `active_only`); v2 body |
| GET | `/symbols/search` | **Alias** — same handler as `GET /symbols` (SPEC path) |
| GET | `/symbols/{symbol}` | v2 body |

---

### Replay REST chunks (D-80)

#### `POST /replay/runs`

Creates an in-memory replay run (wraps `ReplayService.create_session`).

**Body**

```json
{
  "symbolId": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "end": 1706745600,
  "indicators": [{ "key": "RSI", "params": { "period": 14 } }],
  "stepTimeframe": null
}
```

**Response `201`**

```json
{
  "runId": "550e8400-e29b-41d4-a716-446655440000",
  "symbolId": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "end": 1706745600,
  "totalBars": 744
}
```

`runId` === internal `session_id`. Existing `POST /replay/sessions` remains; optional
deprecation note in OpenAPI.

#### `GET /replay/{run_id}/chunk`

Returns a **`ChartDataResponse`** slice for frontend buffering.

**Query**

| Param | Required | Default | Notes |
|---|---|---|---|
| `from` | yes | — | Unix seconds — first bar **at or after** this time |
| `limit` | no | **500** | Max bars in chunk; max **5000** |

**Behaviour**

1. Load session by `run_id`; 404 if missing/expired.
2. Find first bar index where `bar.time >= from`.
3. Return up to `limit` consecutive bars from preloaded `session.bars`.
4. Compute indicators on **prefix** of `session.frame` through the **last bar in the chunk**
   (same semantics as WS `step` — indicators reflect replay-visible history only).
5. `signals`: `[]`; `trades`: `[]` in 4b.
6. Include `symbol` structured entity and `timeframe` from session.

**Response:** Same schema as `GET /chart-data` (subset window). `start`/`end` in response
reflect the chunk's actual bar range, not the full run range.

**Pagination:** Client sets next `from` to `last_bar.time + bar_period_seconds` (or uses
`nextStart` if provided). Document bar-period helper in `api/services/timeframes.py`.

#### `GET /replay/{run_id}/trades`

**4b response:** `{ "runId": "...", "trades": [] }`

Phase 4d populates from backtest trade log when `run_id` references a backtest run.

#### `DELETE /replay/{run_id}`

Alias for `DELETE /replay/sessions/{session_id}` — tear down run.

---

## WebSocket Replay (unchanged)

`/ws/replay/{session_id}` continues to work. Phase 4b does **not** remove or modify WS
message shapes. Frontend MVP ignores replay WS (D-80).

---

## Frontend Integration Map

| SPEC-001 component | Phase 4b endpoint |
|---|---|
| `useChartData` | `GET /chart-data` |
| `useChunkManager` prefetch | `GET /chart-data` with sliding `start`/`end` + `nextStart` |
| `chartStore.symbol` | `Symbol` from chart-data or `GET /symbols/{id}` |
| `SymbolSearch` | `GET /symbols/search?q=` |
| `replayStore.init(runId)` | `POST /replay/runs` → `runId` |
| `replayStore.appendChunk` | `GET /replay/{runId}/chunk?from=&limit=` |
| `replayStore.trades` | `GET /replay/{runId}/trades` (empty until 4c) |
| `drawingStore` / workspace | **Phase 4d** — not 4b |

---

## Implementation Steps

### Step 1 — Schema and migration

1. Add `V006__symbol_metadata.sql`.
2. Extend `SymbolRepository` / `SymbolService` for new columns.
3. Update seed values for tick/lot sizes.
4. Extend `SymbolResponse` to SPEC shape (`id`, `ticker`, `baseAsset`, …).

### Step 2 — Chart data service

1. Add `api/schemas/chart_data.py` (`ChartDataRequest`, `ChartDataResponse`, `Signal`, `Trade`).
2. Add `ChartDataService` composing candle + indicator services.
3. Add `routers/chart_data.py` + register in `main.py`.
4. Implement indicator map keying strategy.
5. Add `nextStart` pagination cursor.

### Step 3 — Symbol search alias

1. Add `GET /symbols/search` route pointing to `list_symbols`.
2. Update OpenAPI + Postman.

### Step 4 — Replay chunks

1. Add `ReplayRunCreate` / `ReplayRunResponse` schemas.
2. `ReplayService.get_chunk(run_id, from_ts, limit)` — slice bars + prefix indicators.
3. Routes: `POST /replay/runs`, `GET /replay/{run_id}/chunk`, `GET /replay/{run_id}/trades`, `DELETE /replay/{run_id}`.
4. Map `run_id` ↔ `session_id` internally (same UUID).

### Step 5 — Tests

| Test file | Coverage |
|---|---|
| `test_chart_data.py` | Happy path; indicators bundled; empty signals/trades; limit; 404 symbol |
| `test_replay_chunks.py` | Create run → fetch chunks → sequential `from`; 404 run |
| `test_symbols_v2.py` | v2 fields present; search alias |
| Extend `test_integration.py` | Optional smoke with mocked DB |

Target: **+15–20 tests**, full suite green.

### Step 6 — Documentation

1. Update [openapi.yaml](openapi.yaml).
2. Postman folder **Chart Data** + **Replay Chunks**.
3. Update [PHASE_4_HLD.md](PHASE_4_HLD.md) cross-link (4b supersedes FE-facing gaps).
4. Update [SPEC-001 §13](../../frontend/docs/SPEC-001.md) status when complete.

---

## Testing Strategy

- **Unit:** `ChartDataService` with mocked `CandleService` / `IndicatorService`.
- **Replay chunks:** Use existing replay test fixtures; assert chunk boundaries and indicator prefix.
- **Migration:** Verify V006 applies on clean DB and upgrades V005 databases.
- **Regression:** All 342+ existing tests must pass unchanged.
- **Manual smoke:**
  ```bash
  cd backend && python -m api
  curl "http://localhost:8000/api/v1/chart-data?symbolId=BTC/USDT&timeframe=1h&start=...&end=..."
  ```

---

## Done Criteria

Phase 4b is **complete** when:

- [x] `V006` migration applied; symbols return structured v2 shape
- [x] `GET /chart-data` returns candles + indicators in one response; `limit` 500 default / 5000 max
- [x] `GET /symbols/search` alias works
- [x] `POST /replay/runs` + `GET /replay/{run_id}/chunk` return `ChartDataResponse` chunks
- [x] `GET /replay/{run_id}/trades` returns empty list (contract stub for 4c)
- [x] Phase 4 endpoints + replay WS still pass all existing tests
- [x] OpenAPI + Postman updated
- [x] Full test suite green (350 tests as of 2026-06-09)
- [x] SPEC-001 §13 gaps for 4b items marked resolved

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Large `indicators` query strings on GET | Document POST `/chart-data/query` as optional stretch if URL length bites; MVP uses GET |
| `run_id` confusion with future backtest runs | Document 4b `run_id` = replay session; 4c adds `source: "backtest" \| "replay"` |
| Duplicate logic vs WS step | Extract shared `compute_prefix_indicators(session, end_index)` in `ReplayService` |
| Symbol v2 breaking early adapters | Ship before FE; document field mapping in SPEC-001 §13 |

---

## Relationship to Other Phases

```
Phase 4  ──► Phase 4b (this doc) ──► FE Phase 1–4 can ship without client adapter
                │
                ├── Phase 4c — Replay V2 (WebSocket streaming)
                ├── Phase 4d — backtest API, trades/signals in chart-data
                ├── Phase 4d — workspace sync (drawings, layouts)
                │
Phase 5 (market structure) — parallel; no 4b dependency
Phase 11 — auth, live WS, replay DB persistence
```

---

## References

- [PHASE_4_HLD.md](PHASE_4_HLD.md)
- [SPEC-001 — Frontend](../../frontend/docs/SPEC-001.md)
- [DECISIONS.md — D-80–D-87](DECISIONS.md#frontend-architecture-spec-001--locked-2026-06-09)
- [ROADMAP.md](ROADMAP.md)
- [openapi.yaml](openapi.yaml)
