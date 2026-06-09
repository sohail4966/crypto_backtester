# Phase 4 High Level Design — Client API Layer (REST + WebSocket)

**Status:** Approved — implementation complete  
**Prerequisite:** Phase 3 complete ([PHASE_3_HLD.md](PHASE_3_HLD.md))  
**Supersedes:** Previous Phase 4 (Market Structure Detection) — moved to **Phase 5**  
**Next phase after this:** [Phase 5 — Market Structure Detection](ROADMAP.md#phase-5--market-structure-detection)

---

## Why Phase 4 Is the API Layer

Phases 1–3 built a trustworthy **data → indicators → backtest** spine. Before adding
market structure, patterns, or SMC, the platform needs a **client-facing surface** that
a TradingView-like chart application can consume:

| Client capability | Needs from backend |
|---|---|
| Symbol picker | `symbols` table + list API |
| Historical chart | Past OHLCV via REST |
| Indicator overlays | Server-side compute (REST + replay WS) |
| Watchlists | Per-user persisted lists (`user_id` scoped) |
| Users | Name + email stored (no login in Phase 4) |
| Bar replay | WebSocket stepped playback + indicators at variable speed |

**No live chart tail in Phase 4** — only historical candles and replay-emitted candles.

**Market structure (Phase 5):** D-53–D-66 in [DECISIONS.md](DECISIONS.md) apply there, not here.

---

## Phase 4 Goal

Deliver a **HTTP + WebSocket API** (all routes **public**, no authentication) with:

1. **Symbols** — DB-backed catalog (3 coins now; extendible later).
2. **Candles** — paginated historical OHLCV (`limit` default **1000**, max **5000**).
3. **Indicators** — catalog + batch compute on historical windows.
4. **Users** — CRUD `name` + `email` (no passwords, no JWT).
5. **Watchlists** — CRUD per `user_id`.
6. **Bar replay** — in-memory sessions; WebSocket emits candles + indicator prefix per step.

**Explicitly out of scope for Phase 4**

- Authentication / authorization (deferred → **Phase 11**).
- Live candle streaming / real-time chart tail (deferred → **Phase 11**).
- Replay session DB persistence (deferred → **Phase 11**).
- React / frontend UI (Phase 11).
- Market structure, patterns, SMC (Phases 5–7).
- Backtest execution via API.
- Exchange WebSocket feeds.

---

## Client Feature Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     Chart Client (TV-like)                       │
├─────────────┬──────────────┬──────────────┬─────────────────────┤
│ Symbol pick │ Past candles │ Indicators   │ Users / Watchlists  │
│ (REST)      │ (REST)       │ (REST)       │ (REST, user_id)     │
├─────────────┴──────────────┴──────────────┴─────────────────────┤
│ Bar Replay: REST create session → WS play/step + candles + ind. │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST (history) + WS (replay only)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Phase 4 API Server                          │
│  FastAPI  │  Symbols  │  Candles  │  Indicators  │  Replay (mem) │
└───────────────────────────────┬─────────────────────────────────┘
                                │ get_candles() only (D-06)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│   TimescaleDB: candles hypertable + app.symbols, users, lists   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Principles

| ID | Rule | Phase 4 application |
|---|---|---|
| D-06 | `get_candles()` is the only candle boundary | API never queries `candles` SQL directly |
| D-07 | Pure functions for compute | Indicator calls use `indicators.registry` |
| D-69 | No auth in Phase 4 | All endpoints public; `user_id` scopes watchlists |
| D-76 | Symbols in DB table | Catalog from `app.symbols`, not `data.yaml` at runtime |

### Layering

```
api/
  main.py                 # FastAPI app, lifespan, CORS
  deps.py                 # DB session, settings
  routers/
    symbols.py            # catalog from app.symbols
    candles.py            # historical OHLCV
    indicators.py         # catalog + compute
    users.py              # CRUD name + email
    watchlists.py         # CRUD scoped by user_id
    replay.py             # REST: create/get/delete replay sessions
  ws/
    replay.py             # replay control + candle/indicator events
  schemas/
  services/
    candle_service.py
    indicator_service.py
    symbol_service.py
    replay_service.py     # in-memory session store only
  repositories/
    symbol_repository.py
    user_repository.py
    watchlist_repository.py
```

No `auth.py`, no `auth_service.py`, no `ws/live.py`, no `replay_repository.py` in Phase 4.

---

## Technology Stack

| Component | Choice |
|---|---|
| HTTP + WS | **FastAPI** + **uvicorn** |
| App persistence | PostgreSQL (`app` schema), same `DATABASE_URL` |
| Migrations | `V005__app_schema.sql` |
| Tests | `httpx` + `pytest-asyncio` |

**New dependencies:**

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.27.0
pytest-asyncio>=0.24.0
```

No JWT / passlib / python-jose in Phase 4.

---

## Data Model (App Schema)

Migration: `data/migrations/sql/V005__app_schema.sql`

### `app.symbols`

Canonical symbol catalog — **source of truth for the API**, seeded with Phase 1 universe.

| Column | Type | Notes |
|---|---|---|
| `symbol` | TEXT PK | e.g. `BTC/USDT` |
| `base` | TEXT NOT NULL | `BTC` |
| `quote` | TEXT NOT NULL | `USDT` |
| `is_active` | BOOLEAN | Default `true`; soft-disable without delete |
| `sort_order` | INT | Display order |
| `created_at` | TIMESTAMPTZ | |

**Seed data (V005):** `BTC/USDT`, `ETH/USDT`, `SOL/USDT` (from Phase 1 universe).
Future symbols: `INSERT` into `app.symbols` + ensure candle data exists — no code change.

### `app.users`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `name` | TEXT NOT NULL | Display name |
| `email` | TEXT UNIQUE NOT NULL | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

No `password_hash`. No `is_active` gate in Phase 4 (optional soft-delete stretch).

### `app.watchlists`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | CASCADE delete |
| `name` | TEXT NOT NULL | |
| `is_default` | BOOLEAN | One default per user |
| `sort_order` | INT | |
| `created_at` | TIMESTAMPTZ | |

### `app.watchlist_symbols`

| Column | Type | Notes |
|---|---|---|
| `watchlist_id` | UUID FK | PK with `symbol_id` |
| `symbol_id` | TEXT FK → symbols.symbol | Enforces valid symbols |
| `sort_order` | INT | |

### Replay sessions — **not in DB (Phase 4)**

In-memory dict keyed by `session_id` in `replay_service.py`. Lost on process restart.
Persistence deferred to **Phase 11** (D-78).

---

## Supported Timeframes

All TFs from `get_candles()` / repository:

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`, `1w`, `1M` (from `DERIVED_INTERVALS` + `1m`)

Expose via `GET /api/v1/meta/timeframes`.

---

## API Reference (canonical)

**Machine-readable spec:** [openapi.yaml](openapi.yaml) — all REST endpoints with
request/response schemas, error codes, and WebSocket message types under `x-websocket`.

**Live docs:** `http://localhost:8000/docs` (FastAPI Swagger UI, REST only).

## REST API Specification

Base: **`/api/v1`**. All routes **public** (no `Authorization` header). JSON bodies.
Candle `time` = **Unix seconds UTC** (D-70).

> The tables below are a summary. For full request/response bodies, see [openapi.yaml](openapi.yaml).

### Meta

| Method | Path | Description |
|---|---|---|
| GET | `/meta/timeframes` | Supported timeframe strings |
| GET | `/meta/health` | DB reachable, API version |

### Symbols

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/symbols` | `q?`, `active_only?` (default true) | `[{symbol, base, quote, is_active, sort_order}]` |
| GET | `/symbols/{symbol}` | | Single row or `404` |

Symbol must exist in `app.symbols` **and** be active for candle/replay requests.

### Candles (historical only)

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/candles/{symbol}` | `timeframe`, `from`, `to`, `limit?` | See below |

| Param | Default | Max |
|---|---|---|
| `limit` | **1000** (D-79) | **5000** |

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "bars": [{"time": 1704067200, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}],
  "next_from": 1704074400
}
```

- `from` / `to`: inclusive unix seconds.
- `next_from` present when more bars exist beyond `limit`.
- Unknown symbol (not in `app.symbols`) → `404`.

### Indicators

| Method | Path | Description |
|---|---|---|
| GET | `/indicators` | Registry catalog |
| POST | `/indicators/compute` | Batch compute (no auth) |

Request/response shape unchanged from prior draft; warmup → `value: null`.

### Users

| Method | Path | Body / notes |
|---|---|---|
| POST | `/users` | `{name, email}` → `{id, name, email, created_at}` |
| GET | `/users` | List all users (paginated) |
| GET | `/users/{user_id}` | Single user |
| PATCH | `/users/{user_id}` | `{name?, email?}` |
| DELETE | `/users/{user_id}` | Delete user + watchlists (CASCADE) |

**Trust model:** Any client can read/write any `user_id`. Acceptable for local/dev Phase 4;
Phase 11 adds auth and ownership checks.

### Watchlists

Scoped by path `user_id` (no auth).

| Method | Path | Description |
|---|---|---|
| GET | `/users/{user_id}/watchlists` | All lists with symbols |
| POST | `/users/{user_id}/watchlists` | `{name, symbols: ["BTC/USDT", ...]}` |
| GET | `/users/{user_id}/watchlists/{id}` | Detail |
| PATCH | `/users/{user_id}/watchlists/{id}` | Rename, `is_default`, `sort_order` |
| DELETE | `/users/{user_id}/watchlists/{id}` | Delete |
| PUT | `/users/{user_id}/watchlists/{id}/symbols` | Replace ordered symbol list |

Symbols in watchlists must reference active `app.symbols` rows.

**On user create (OQ-54):** optionally auto-create **"Default"** watchlist with all
active symbols — implement in `user_service` (recommended).

### Replay (REST control plane)

| Method | Path | Description |
|---|---|---|
| POST | `/replay/sessions` | Create in-memory session |
| GET | `/replay/sessions/{id}` | Snapshot |
| DELETE | `/replay/sessions/{id}` | Tear down |

**Create body:**

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "end": 1735689600,
  "indicators": [{"key": "RSI", "params": {"period": 14}}],
  "step_timeframe": "1h",
  "speed": 1.0,
  "autoplay": false
}
```

Response: `{"session_id": "...", "ws_url": "/ws/replay/{session_id}"}`

Optional `user_id` in body for logging only — not required.

---

## WebSocket — Replay Only

**Single WS surface in Phase 4:** `WS /ws/replay/{session_id}` — no auth token.

### Client commands

| action | payload | Effect |
|---|---|---|
| `play` | `{speed?: 2.0}` | Autoplay |
| `pause` | | Pause |
| `step` | `{count?: 1}` | Advance N bars |
| `seek` | `{to: 1704067200}` | Jump cursor |
| `set_speed` | `{speed: 5.0}` | Bars per second |
| `set_step_timeframe` | `{step_timeframe: "15m"}` | Change step TF |
| `set_indicators` | `{indicators: [...]}` | Replace indicators |
| `get_state` | | Full snapshot |

### Server events

```json
{"type": "replay_state", "cursor": 1704067200, "state": "playing", "speed": 1.0, "bar_index": 42, "total_bars": 5000}
```

```json
{"type": "candle", "bar": {"time": 1704067200, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}}
```

```json
{"type": "indicators", "series": [{"key": "RSI", "params": {"period": 14}, "points": [{"time": 1704067200, "value": 55.1}]}]}
```

```json
{"type": "replay_completed"}
```

```json
{"type": "error", "code": "SEEK_OUT_OF_RANGE", "message": "..."}
```

Each step emits **one candle** + **indicator values for the prefix** `bars[0..cursor]` only
(no lookahead). Autoplay interval: `max(50ms, 1/speed)`.

Sessions expire after **30 min** idle or on disconnect.

---

## Indicator Service

Unchanged core: `compute_indicators(candles, specs)` via `indicators.registry`.

- **REST:** full window for chart initial load.
- **Replay WS:** prefix recompute each step (MVP: full prefix; optimize later if needed).

---

## Security (Phase 4)

| Topic | Decision |
|---|---|
| Authentication | **None** — all APIs public (D-69) |
| `user_id` | Opaque UUID; client stores locally |
| CORS | `CORS_ORIGINS` env for SPA dev |
| HTTPS | Reverse proxy in production |
| Abuse | Local/trusted network assumed; rate limiting stretch |

Phase 11 adds JWT, protected routes, and replay persistence.

---

## Error Model

```json
{"error": {"code": "SYMBOL_NOT_FOUND", "message": "Unknown symbol: FOO/USDT"}}
```

| HTTP | Code | When |
|---|---|---|
| 400 | `INVALID_REQUEST` | Malformed body |
| 404 | `NOT_FOUND` | Symbol, user, watchlist, replay session |
| 422 | `VALIDATION_ERROR` | Invalid TF, symbol inactive, bad indicator key |
| 500 | `INTERNAL_ERROR` | Unhandled |

No `401` / `403` in Phase 4.

---

## Configuration

```yaml
api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:5173
  replay:
    max_window_bars: 50000
    session_idle_minutes: 30
    min_step_interval_ms: 50
  candles:
    default_limit: 1000
    max_limit: 5000
```

Entry: `uvicorn api.main:app --reload`

---

## Implementation Steps

Each step is independently verifiable. Complete steps in order.

### Step 0 — Q&A gate ✅

**Complete.** D-67–D-79 and OQ-52–OQ-58 recorded in [DECISIONS.md](DECISIONS.md) and
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

### Step 1 — Infrastructure

**Build**

- Add to `requirements.txt`: `fastapi`, `uvicorn[standard]`, `httpx`, `pytest-asyncio`.
- Create `api/` package layout (`main.py`, `deps.py`, `routers/`, `ws/`, `schemas/`,
  `services/`, `repositories/`).
- `api/main.py`: FastAPI app factory, CORS from config/env, router registration, lifespan.
- `api/deps.py`: settings (`API_HOST`, `API_PORT`, `CORS_ORIGINS`), DB connection helper
  reusing `data.db` / repository patterns.
- Global exception handler → consistent `{"error": {code, message}}` JSON (see Error Model).
- `data/migrations/sql/V005__app_schema.sql`:
  - `CREATE SCHEMA app`
  - `app.symbols` + seed `BTC/USDT`, `ETH/USDT`, `SOL/USDT`
  - `app.users` (`id`, `name`, `email`, timestamps)
  - `app.watchlists`, `app.watchlist_symbols` (FK to `symbols.symbol`)
- Wire migration into existing startup path (same as `run_backtest.py` migration runner).
- `GET /api/v1/meta/health`, `GET /api/v1/meta/timeframes`.

**Files (new)**

```
api/__init__.py
api/__main__.py              # python -m api
api/main.py
api/deps.py
api/schemas/common.py
api/schemas/meta.py
api/routers/meta.py
data/migrations/sql/V005__app_schema.sql
```

**Verify**

```bash
pip install -r requirements.txt
docker compose up -d
pytest tests/api/test_meta.py -q
curl http://localhost:8000/api/v1/meta/health
```

---

### Step 2 — Symbols REST

**Build**

- `api/repositories/symbol_repository.py` — list, get by symbol, `is_active` filter.
- `api/services/symbol_service.py` — search by `q` on symbol/base.
- `api/schemas/symbols.py` — `SymbolResponse`.
- `api/routers/symbols.py`:
  - `GET /api/v1/symbols`
  - `GET /api/v1/symbols/{symbol}`

**Verify**

```bash
pytest tests/api/test_symbols.py -q
curl http://localhost:8000/api/v1/symbols
# Expect 3 rows: BTC/USDT, ETH/USDT, SOL/USDT
```

---

### Step 3 — Historical candles REST

**Build**

- `api/services/candle_service.py`:
  - Wrap `get_candles(symbol, timeframe, start, end)` (D-06).
  - Validate symbol against `app.symbols` (active only).
  - Convert `ts` → Unix seconds (D-70).
  - Apply `limit` default **1000**, cap **5000** (D-79).
  - Return `next_from` cursor when truncated.
- `api/schemas/candles.py` — `Bar`, `CandlesResponse`.
- `api/routers/candles.py` — `GET /api/v1/candles/{symbol}`.

**Verify**

```bash
pytest tests/api/test_candles.py -q
curl "http://localhost:8000/api/v1/candles/BTC/USDT?timeframe=1d&from=1704067200&to=1735689600"
curl "http://localhost:8000/api/v1/candles/BTC/USDT?timeframe=1d&from=1704067200&to=1735689600&limit=100"
# Unknown symbol → 404; limit=9999 → 422
```

---

### Step 4 — Indicators REST

**Build**

- `api/services/indicator_service.py`:
  - `list_catalog()` from `INDICATORS` + `INDICATOR_META` (default params map).
  - `compute(symbol, timeframe, from, to, specs)` — load candles once, batch compute.
  - `NaN` → JSON `null`; shared_params grouping (MACD, BB, Ichimoku).
- `api/schemas/indicators.py` — `IndicatorSpec`, `IndicatorSeries`, compute request/response.
- `api/routers/indicators.py`:
  - `GET /api/v1/indicators`
  - `POST /api/v1/indicators/compute`

**Verify**

```bash
pytest tests/api/test_indicators.py -q
# RSI warmup nulls, MACD_HIST multi-key, unknown key → 422
```

---

### Step 5 — Users REST

**Build**

- `api/repositories/user_repository.py` — CRUD on `app.users`.
- `api/services/user_service.py`:
  - Create user `{name, email}`.
  - On create: auto-create **"Default"** watchlist with all active symbols (OQ-54).
- `api/schemas/users.py`.
- `api/routers/users.py`:
  - `POST /api/v1/users`
  - `GET /api/v1/users` (paginated)
  - `GET /api/v1/users/{user_id}`
  - `PATCH /api/v1/users/{user_id}`
  - `DELETE /api/v1/users/{user_id}`

**Verify**

```bash
pytest tests/api/test_users.py -q
# Duplicate email → 422; delete cascades watchlists
```

---

### Step 6 — Watchlists REST

**Build**

- `api/repositories/watchlist_repository.py` — CRUD + symbol ordering.
- `api/services/watchlist_service.py` — validate symbols exist in `app.symbols`.
- `api/schemas/watchlists.py`.
- `api/routers/watchlists.py` under `/api/v1/users/{user_id}/watchlists`:
  - `GET`, `POST`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`
  - `PUT /{id}/symbols`

**Verify**

```bash
pytest tests/api/test_watchlists.py -q
# Invalid symbol in list → 422; wrong user_id on nested id → 404
```

---

### Step 7 — Replay service + REST

**Build**

- `api/services/replay_service.py` — **in-memory** `dict[session_id, ReplaySession]` (D-71):
  - Preload step-TF OHLCV via `get_candles()` for `[start, end]`.
  - Cursor index, state (`idle` | `playing` | `paused` | `completed`).
  - `create`, `get`, `delete`, `step`, `seek`, `set_speed`, `set_indicators`.
  - Idle expiry (30 min); `max_window_bars` guard.
  - On step: return bar + indicator prefix snapshot (bars `0..cursor`, no lookahead).
- `api/schemas/replay.py`.
- `api/routers/replay.py`:
  - `POST /api/v1/replay/sessions`
  - `GET /api/v1/replay/sessions/{id}`
  - `DELETE /api/v1/replay/sessions/{id}`

**Verify**

```bash
pytest tests/api/test_replay_service.py -q
# Session gone after delete; seek out of range → error
```

---

### Step 8 — Replay WebSocket

**Build**

- `api/ws/replay.py` — `WS /ws/replay/{session_id}` (no auth):
  - Parse client commands: `play`, `pause`, `step`, `seek`, `set_speed`,
    `set_step_timeframe`, `set_indicators`, `get_state`.
  - Emit server events: `replay_state`, `candle`, `indicators`, `replay_completed`, `error`.
  - Autoplay asyncio task: interval `max(50ms, 1/speed)` between bars.
  - Clean up session task on disconnect.
- Register WS route in `api/main.py`.

**Verify**

```bash
pytest tests/api/test_replay_ws.py -q
# step count=3 advances cursor by 3; indicator at bar N matches REST compute on prefix
```

---

### Step 9 — Integration tests + entrypoint

**Build**

- `tests/api/conftest.py` — FastAPI test client, test DB fixtures.
- `tests/api/test_integration.py` — end-to-end flow:
  1. `GET /symbols`
  2. `GET /candles/BTC/USDT`
  3. `POST /indicators/compute`
  4. `POST /users` → `POST /watchlists`
  5. `POST /replay/sessions` → WS step through 5 bars
- `api/__main__.py` — `uvicorn api.main:app` entry.
- README section: **Running the API**.

**Verify**

```bash
pytest tests/api/ -q
pytest -q   # full suite still green
uvicorn api.main:app --reload --port 8000
open http://localhost:8000/docs
```

---

### Step 10 — Documentation sign-off

**Build**

- Phase 4 completion section in this doc (below).
- Update [ROADMAP.md](ROADMAP.md) status to complete when done criteria pass.
- [Done Criteria](#done-criteria) checklist.

**Verify**

- All done criteria checked.
- No `ws/live.py`, no auth middleware, no JWT deps in `requirements.txt`.

---

### Target file tree (end state)

```
api/
  __init__.py
  __main__.py
  main.py
  deps.py
  routers/
    meta.py
    symbols.py
    candles.py
    indicators.py
    users.py
    watchlists.py
    replay.py
  ws/
    replay.py
  schemas/
    common.py
    meta.py
    symbols.py
    candles.py
    indicators.py
    users.py
    watchlists.py
    replay.py
  services/
    symbol_service.py
    candle_service.py
    indicator_service.py
    user_service.py
    watchlist_service.py
    replay_service.py
  repositories/
    symbol_repository.py
    user_repository.py
    watchlist_repository.py

tests/api/
  conftest.py
  test_meta.py
  test_symbols.py
  test_candles.py
  test_indicators.py
  test_users.py
  test_watchlists.py
  test_replay_service.py
  test_replay_ws.py
  test_integration.py

data/migrations/sql/V005__app_schema.sql
```

---

## Testing Strategy

| Layer | Requirement |
|---|---|
| Unit | Pagination, indicator alignment, replay cursor |
| Integration | Symbols from DB; candles for 3 symbols; user + watchlist CRUD |
| Replay | Step/seek/speed; indicators at N use bars 0..N only |
| WS | Replay play/pause/step events |
| Regression | Golden JSON for indicator compute on BTC slice |

---

## Done Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | D-67–D-79 in DECISIONS.md | [x] |
| 2 | `api/` runnable via uvicorn | [x] |
| 3 | `V005` applied: symbols seeded, users, watchlists | [x] |
| 4 | `GET /symbols` returns 3 coins from DB | [x] |
| 5 | Historical candles: default 1000, max 5000 | [x] |
| 6 | Indicator catalog + compute (58 keys) | [x] |
| 7 | User + watchlist CRUD without auth | [x] |
| 8 | Replay WS: candles + indicators, variable speed | [x] |
| 9 | **No** live WS; **no** auth middleware | [x] |
| 10 | OpenAPI at `/docs`; tests green | [x] (`342 passed`, 21 API tests) |

---

## Locked Decisions

| ID | Decision |
|---|---|
| D-67 | FastAPI + uvicorn |
| D-68 | Backend only; UI → Phase 11 |
| D-69 | **No authentication in Phase 4** — all APIs public |
| D-70 | Candle `time` = Unix seconds UTC |
| D-71 | Replay sessions **in-memory** only |
| D-72 | Indicator compute on server via registry |
| D-73 | `app` schema separate from `candles` hypertable |
| D-75 | Market structure → Phase 5; phase renumbering |
| D-76 | **`app.symbols` table** — API catalog source; 3 coins seeded |
| D-77 | Users: **name + email** only; watchlists per `user_id` |
| D-78 | Auth, live WS, replay DB → **deferred Phase 11** |
| D-79 | Candle `limit` default **1000**, max **5000** |

---

## Resolved Q&A

| ID | Decision |
|---|---|
| OQ-52 | No auth for any endpoint |
| OQ-53 | Replay in-memory; DB → Phase 11 |
| OQ-54 | Default watchlist on user create (recommended) |
| OQ-55 | Default limit 1000, max 5000 |
| OQ-56 | `step_timeframe` may differ from display `timeframe` |
| OQ-57 | Batch `POST /indicators/compute` only |
| — | **No live chart streaming** in Phase 4; replay WS only |

---

## Deferred to Phase 11

| Feature | Notes |
|---|---|
| JWT / login / protected routes | Wrap existing user table |
| Live candle WebSocket | Poll or push after sync |
| `app.replay_sessions` persistence | Resume replay across restarts |
| Ownership checks on watchlists | Requires auth |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Open API in shared network | Document local-only; Phase 11 auth |
| Spoofing `user_id` on watchlists | Acceptable Phase 4; auth later |
| Replay memory | `max_window_bars`; coarser step TF for long ranges |
| Indicator latency | `limit` caps; prefix recompute bounded |

---

## References

- [PHASE_3_HLD.md](PHASE_3_HLD.md)
- [PHASE_2_HLD.md](PHASE_2_HLD.md)
- [ROADMAP.md](ROADMAP.md)
- [DECISIONS.md](DECISIONS.md)

---

## Phase 4 Completion Assessment

**Assessment date:** 2026-06-09  
**Rating:** **8.5 / 10**  
**Completion:** **100% for Phase 4 scope** (auth, live WS, replay DB persistence correctly deferred to Phase 11)

Phase 4 delivers a chart-ready **REST + replay WebSocket** layer on top of the existing
data and indicator spine. Historical candles flow through `get_candles()` (D-06); indicators
are computed server-side from the 58-key registry (D-72). Users and watchlists persist in
`app.*` tables; replay sessions are in-memory (D-71). No authentication (D-69).

### Evidence checked

| Check | Result | Notes |
|---|---|---|
| Full unit suite | Passing | `342 passed` (21 API tests) |
| D-67 through D-79 in DECISIONS.md | Done | Includes no-auth, symbols table, candle limits |
| `api/` package | Done | Routers, services, repositories, WS replay |
| `V005__app_schema.sql` | Done | `app.symbols` seeded BTC/ETH/SOL, users, watchlists |
| Symbols REST | Done | `GET /symbols`, search, active filter |
| Candles REST | Done | Unix seconds (D-70), limit 1000/5000 (D-79), `next_from` cursor |
| Indicators REST | Done | Catalog + batch compute; warmup history seeding |
| Users + watchlists | Done | Default watchlist on create (OQ-54); symbol FK validation |
| Replay REST + WS | Done | create/get/delete; step/seek/play/pause; prefix indicators |
| No live WS / no auth | Done | Grep clean; no JWT deps |
| OpenAPI | Done | Live `/docs` + static [openapi.yaml](openapi.yaml) |
| Data boundary | Done | Candles via `get_candles()` only in services |

### Rating breakdown

| Area | Score | Comment |
|---|---|---|
| Architecture alignment | 9/10 | Thin API layer; `app` schema separate from candles (D-73); shared replay singleton |
| Feature completeness | 9/10 | All HLD endpoints shipped; indicator warmup seeding exceeds original spec |
| Correctness / invariants | 8/10 | Replay uses prefix-only indicators; short windows degrade to null safely |
| Test coverage | 8/10 | 21 API tests (services + WS + mocked HTTP); no live-DB API smoke test |
| Documentation | 8.5/10 | HLD, ROADMAP, README, openapi.yaml; static spec may drift from `/docs` |
| Client readiness | 8/10 | Sufficient for Phase 11 UI; no auth means local/trusted-network only |

### Enhancements beyond original HLD

| Enhancement | Notes |
|---|---|
| Indicator warmup history | `indicators/warmup.py` loads pre-window bars so chart-visible range is not all-null |
| Extended timeframes | Repository-aligned: `3m`, `30m`, `2h`, `1w`, `1M` (replaces stale 6h/12h in early draft) |
| Static OpenAPI export | [docs/openapi.yaml](openapi.yaml) documents REST + WS message shapes |

### Known gaps (acceptable for Phase 4)

- **No live-DB API integration test** — HTTP/WS tests mock `connect()` / `get_candles()`; manual `python -m api` + curl against synced DB still recommended.
- **No golden JSON regression** for `POST /indicators/compute` (listed in testing strategy, not implemented).
- **Replay autoplay speed** — WS `play` path exists; automated timing test not added.
- **Public API** — any client can read/write any `user_id` (D-69; Phase 11 auth).
- **In-memory replay** — sessions lost on restart (D-71; Phase 11 persistence).
- **Candle pagination** — `next_from` uses `last_bar_time + 1` second, not bar-period-aware (works for sequential fetch, imprecise for sub-daily TFs).

### Completion verdict

Phase 4 is **complete**. Phase 5 (market structure) can start without API changes.
Phase 11 UI can consume this API as-is for historical charts and bar replay.

---
