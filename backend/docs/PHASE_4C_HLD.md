# Phase 4c High Level Design — Replay V2 (WebSocket Streaming)

**Status:** Not started  
**Prerequisite:** Phase 4b complete ([PHASE_4B_HLD.md](PHASE_4B_HLD.md))  
**Enables:** [FE Phase 3](../frontend/docs/FE_PHASE_3_HLD.md) replay page  
**Decisions:** D-88 through D-94 in [DECISIONS.md](DECISIONS.md)  
**Design spec:** [2026-06-28-replay-v2-design.md](../../docs/superpowers/specs/2026-06-28-replay-v2-design.md)

---

## Why Phase 4c Exists

Phase 4b delivered REST replay chunks and an interim WebSocket step API. Both paths
**recompute indicators over a growing prefix on every step** — too slow for smooth playback
and not extensible for signals or chart patterns.

Phase 4c replaces the replay data path with:

1. **Precomputed rolling buffer** — compute overlays once per buffer segment.
2. **WebSocket tick batches** — O(1) per bar; client-owned playback clock.
3. **Open-ended sessions** — start anchor only; runs until latest candle or user stop.
4. **DB-backed sessions** — metadata + cursor checkpoint; in-memory hot cache.
5. **`OverlayPipeline`** — extensible overlay compute (indicators v1; signals/patterns later).

**REST replay chunk endpoints are removed** (supersedes D-80 for replay transport).

---

## Phase 4c Goal

Deliver near-zero-lag bar replay over WebSocket for candles + indicators.

**In scope**

- `app.replay_sessions` migration + repository
- `ReplayEngine`, `ReplayBuffer`, `OverlayPipeline`
- Refactored `ReplaySessionStore` (DB + in-memory cache)
- WebSocket protocol v2 (`snapshot`, `tick_batch`, `buffer_reset`, …)
- Remove REST chunk routes and dead replay code paths
- Tests, OpenAPI update, decision log entries D-88–D-94

**Out of scope**

- Signals, trades, chart patterns in replay (future `OverlayPipeline` plugins)
- Backtest HTTP API (separate phase; was previously labelled 4c in 4b doc)
- JWT auth (Phase 11)
- Frontend React implementation (FE Phase 3 — parallel once WS v2 ships)

---

## Architecture Overview

```
┌──────────────┐     WebSocket      ┌─────────────────────────────────────┐
│   Frontend   │◄──────────────────►│  api/ws/replay.py                    │
│  tick queue  │   tick_batch       │  (thin handler — no autoplay loop)   │
│  setInterval │   snapshot         └──────────────┬──────────────────────┘
└──────────────┘                                   │
                                                   ▼
                                    ┌──────────────────────────────────────┐
                                    │  ReplayEngine                         │
                                    │  cursor · extend · trim · seek        │
                                    └───────┬──────────────────┬───────────┘
                                            │                  │
                           ┌────────────────┘                  └────────────────┐
                           ▼                                                     ▼
              ┌────────────────────────┐                          ┌─────────────────────────┐
              │  ReplayBuffer           │                          │  ReplaySessionStore      │
              │  frame + overlay arrays │                          │  Postgres + mem cache    │
              └───────────┬────────────┘                          └─────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  OverlayPipeline        │
              │  v1: indicators         │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │  IndicatorService       │
              └────────────────────────┘
```

### Layering (new / modified files)

```
api/
  ws/replay.py                 # MODIFY — v2 events; remove server autoplay loop
  routers/replay.py            # MODIFY — remove chunk/run routes
  schemas/replay.py            # MODIFY — open-ended session; WS event types
  services/
    replay_engine.py           # NEW — cursor, extend, trim, seek, tick slice
    replay_buffer.py           # NEW — frame + precomputed overlay storage
    overlay_pipeline.py        # NEW — extensible overlay compute interface
    replay_session_store.py    # NEW — DB + in-memory cache
    replay_service.py          # MODIFY — delegate to engine; remove get_chunk
  repositories/
    replay_repository.py       # NEW — app.replay_sessions CRUD
data/migrations/sql/
  V007__replay_sessions.sql    # NEW
tests/api/
  test_replay_engine.py        # NEW
  test_replay_buffer.py        # NEW
  test_replay_ws_v2.py         # NEW
  test_replay_sessions_db.py   # NEW
  test_replay_chunks.py        # DELETE or replace with 410 tests
docs/
  DECISIONS.md                 # D-88–D-94
  openapi.yaml                 # UPDATE
```

---

## Data Model

### Migration: `V007__replay_sessions.sql`

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | UUID PK | |
| `symbol` | TEXT NOT NULL FK → `app.symbols.symbol` | |
| `timeframe` | TEXT NOT NULL | Chart timeframe |
| `step_timeframe` | TEXT NOT NULL | Bar step TF |
| `start_anchor` | BIGINT NOT NULL | User-selected start (unix sec) |
| `cursor_ts` | BIGINT NOT NULL | Last revealed bar time |
| `indicators` | JSONB NOT NULL DEFAULT `'[]'` | `IndicatorSpec[]` |
| `speed` | DOUBLE PRECISION NOT NULL DEFAULT 1.0 | Last speed |
| `state` | TEXT NOT NULL | `idle` \| `playing` \| `paused` \| `completed` |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Not persisted:** OHLCV frame, overlay arrays — always rebuilt from candles on load/reconnect.

### ReplayBuffer (in-memory)

| Field | Type | Notes |
|-------|------|-------|
| `frame` | `pd.DataFrame` | OHLCV including warmup |
| `overlays` | `dict[str, ndarray \| list]` | Precomputed per series id |
| `window_start_idx` | `int` | First visible bar index in frame |
| `cursor_idx` | `int` | Last revealed bar index in frame |
| `prefetch_end_idx` | `int` | Last precomputed bar index |

---

## Settings

| Env var | Default | Purpose |
|---------|---------|---------|
| `REPLAY_TRAIL_BARS` | `500` | Max bars kept behind cursor |
| `REPLAY_PREFETCH_BARS` | `1000` | Bars preloaded ahead of cursor |
| `REPLAY_EXTEND_THRESHOLD` | `200` | Start background extend when cursor this close to prefetch edge |
| `REPLAY_TICK_BATCH_SIZE` | `100` | Ticks per `tick_batch` / refill |
| `REPLAY_TICK_REFILL_THRESHOLD` | `20` | Client requests refill below this queue depth |
| `REPLAY_BASE_INTERVAL_MS` | `1000` | 1× speed = 1 bar/sec (client-side) |
| `REPLAY_MIN_INTERVAL_MS` | `50` | Max 20 bars/sec |
| `REPLAY_CHECKPOINT_INTERVAL_SEC` | `30` | Cursor flush to DB |
| `REPLAY_SESSION_IDLE_MINUTES` | `30` | Evict in-memory cache |

---

## Session Lifecycle

### Create

```http
POST /api/v1/replay/sessions
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "indicators": [{ "key": "RSI", "params": { "period": 14 } }],
  "stepTimeframe": null,
  "speed": 1.0
}
```

**Response `201`**

```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "wsUrl": "ws://localhost:8000/ws/replay/550e8400-e29b-41d4-a716-446655440000"
}
```

**Server steps:**

1. Insert `app.replay_sessions` row (`cursor_ts = start - 1 bar`, state `paused`).
2. Build initial buffer: `[start - warmup .. start + prefetch]` from DB.
3. Run `OverlayPipeline.compute()` once over frame.
4. Cache `ReplayBuffer` in memory.

No `end` date. Replay runs until latest DB candle or user stops.

### Play / tick

1. Client sends `{ "action": "play", "speed": 5 }`.
2. Server slices `tick_batch` of up to `REPLAY_TICK_BATCH_SIZE` ticks from buffer.
3. Client drains queue at `max(50, 1000 / speed)` ms per bar.
4. Client sends `{ "action": "refill" }` when queue `< REPLAY_TICK_REFILL_THRESHOLD`.
5. On each tick advance: trim trail if `> REPLAY_TRAIL_BARS` behind cursor.
6. Checkpoint cursor to DB on pause, disconnect, or interval.

### Forward extend

When `cursor_idx >= prefetch_end_idx - REPLAY_EXTEND_THRESHOLD`:

1. Emit `buffer_loading`.
2. Fetch next segment from DB (up to `prefetch` bars, cap at latest candle).
3. Append to frame; compute overlays for new rows only.
4. Emit `buffer_ready { bufferEnd, latestAvailable }`.

If latest candle reached during extend → next tick emits `replay_completed`.

### Seek

| Case | Behavior |
|------|----------|
| Target within trail window (≤500 bars back) | Move cursor only — instant |
| Target forward within prefetch | Move cursor only |
| Target beyond trail or prefetch | Reload buffer at target; `buffer_reset` + `snapshot` |

### Reconnect

1. `WS /ws/replay/{sessionId}`.
2. Load metadata from DB; rebuild buffer at `cursor_ts`.
3. Send `replay_state` + `snapshot` (trail bars + overlays to cursor).
4. Client resumes from queue refill.

---

## WebSocket Protocol v2

### Client → server

| Action | Payload |
|--------|---------|
| `play` | `{ speed?: number }` |
| `pause` | — |
| `step` | `{ count?: number }` |
| `seek` | `{ to: unix }` |
| `set_speed` | `{ speed: number }` |
| `refill` | — |
| `set_indicators` | `{ indicators: IndicatorSpec[] }` |
| `get_state` | — |

### Server → client

| Event | When |
|-------|------|
| `replay_state` | Connect, pause, seek, state change |
| `snapshot` | Connect, reconnect, seek reload, indicator change |
| `tick_batch` | Play, step, refill |
| `buffer_loading` | Forward extend started |
| `buffer_ready` | Forward extend complete |
| `buffer_reset` | Seek reload or indicator change |
| `replay_completed` | Latest candle passed |
| `error` | `{ code, message }` |

### `tick_batch` shape

```json
{
  "type": "tick_batch",
  "ticks": [
    {
      "bar": { "time": 1704153600, "open": 42000, "high": 42500, "low": 41800, "close": 42200, "volume": 100 },
      "indicators": { "RSI_14": { "time": 1704153600, "value": 52.1 } }
    }
  ],
  "cursor": 1704157200,
  "queueRemaining": 87
}
```

**Removed events:** separate per-tick `candle` + full `indicators` series messages.

---

## OverlayPipeline

Extensible interface for all chart overlays:

```python
class OverlayPipeline:
    def warmup_bars(self, specs: list[OverlaySpec]) -> int: ...
    def compute(self, frame: pd.DataFrame, specs: list[OverlaySpec]) -> OverlayResult: ...
```

**v1:** `IndicatorOverlayComputer` wraps `IndicatorService.compute_on_dataframe`.  
**Future:** `SignalOverlayComputer`, `PatternOverlayComputer` — same buffer, same tick slice.

Tick emission reads precomputed arrays — never calls compute per tick.

---

## REST API Changes

### Removed

| Method | Path | Replacement |
|--------|------|-------------|
| POST | `/api/v1/replay/runs` | `POST /api/v1/replay/sessions` |
| GET | `/api/v1/replay/{run_id}/chunk` | WS `tick_batch` + `snapshot` |
| GET | `/api/v1/replay/{run_id}/trades` | Phase 4 backtest API (future) |
| DELETE | `/api/v1/replay/{run_id}` | `DELETE /api/v1/replay/sessions/{id}` |

Return **410 Gone** with `{ "code": "REPLAY_REST_DEPRECATED", "message": "..." }` for one release, then remove.

### Kept / updated

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/replay/sessions` | Open-ended session; no `end` |
| GET | `/api/v1/replay/sessions/{id}` | State snapshot |
| DELETE | `/api/v1/replay/sessions/{id}` | Teardown DB + cache |
| WS | `/ws/replay/{session_id}` | v2 protocol |

`GET /chart-data` unchanged — used for live chart, not replay playback.

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Seek before `start_anchor` | `error: SEEK_OUT_OF_RANGE` |
| Seek after latest candle | Move cursor to latest; `replay_completed` on next forward step |
| Session not found | WS close 4404; REST 404 |
| Idle timeout | Evict memory; DB row kept |
| Indicator change mid-play | Pause → recompute → `buffer_reset` |
| Concurrent WS | v1: last connection wins; prior gets `SUPERSEDED` + close |
| Extend at latest candle | `buffer_ready` with `latestAvailable`; no more forward data |

---

## Testing Strategy

| Test file | Covers |
|-----------|--------|
| `test_replay_buffer.py` | Load, trim, extend, overlay precompute |
| `test_replay_engine.py` | Step O(1), seek cases, open-ended end |
| `test_replay_ws_v2.py` | tick_batch, snapshot, refill, reconnect |
| `test_replay_sessions_db.py` | CRUD, checkpoint, idle eviction + reload |
| `test_replay_rest_deprecated.py` | Chunk/run routes return 410 |

**Performance assertion:** Step N times — wall time must not grow linearly with N (O(1) per tick).

---

## Implementation Steps

### Step 1 — Schema and repository

1. Add `V007__replay_sessions.sql`.
2. Add `ReplayRepository` + `ReplaySessionStore`.
3. Tests for CRUD and checkpoint.

### Step 2 — Buffer and pipeline

1. Add `ReplayBuffer`, `OverlayPipeline`, `IndicatorOverlayComputer`.
2. Batch compute on load/extend; tick slice helper.
3. Unit tests for trim/extend.

### Step 3 — ReplayEngine

1. Replace prefix-recompute logic in `ReplayService` with `ReplayEngine`.
2. Wire create, step, seek, extend, checkpoint.
3. Service tests.

### Step 4 — WebSocket v2

1. Update `api/ws/replay.py` — remove autoplay loop; add v2 events.
2. Integration tests.

### Step 5 — REST cleanup

1. Remove chunk/run routes; add 410 deprecation shim if needed.
2. Update OpenAPI, Postman, DECISIONS.md.
3. Delete `test_replay_chunks.py` or replace.

### Step 6 — Frontend handoff

1. Update [FE_PHASE_3_HLD.md](../frontend/docs/FE_PHASE_3_HLD.md) and [SPEC-001 §4.5](../frontend/docs/SPEC-001.md).
2. Document WS protocol in OpenAPI / dedicated `REPLAY_WS.md`.

---

## Done Criteria

Phase 4c is **complete** when:

- [ ] `V007` migration applied; sessions persist across process restart (metadata + cursor)
- [ ] WS v2: `snapshot` + `tick_batch` + `refill` work end-to-end
- [ ] Tick latency O(1) — no prefix recompute per step
- [ ] Rolling trail trim + forward extend work at configured thresholds
- [ ] Open-ended replay stops at latest DB candle with `replay_completed`
- [ ] REST chunk/run routes removed or return 410
- [ ] D-88–D-94 recorded in DECISIONS.md
- [ ] OpenAPI + tests updated; full suite green

---

## Relationship to Other Phases

```
Phase 4b (REST chunks) ──► Phase 4c (this doc) ──► FE Phase 3
                                │
                                ├── OverlayPipeline ← signals (4 backtest), patterns (5)
                                ├── Backtest HTTP + trades — separate future phase
                                └── Phase 11 — auth, live WS (unchanged deferral)
```

---

## References

- [PHASE_4B_HLD.md](PHASE_4B_HLD.md)
- [PHASE_4_HLD.md](PHASE_4_HLD.md)
- [DECISIONS.md](DECISIONS.md)
- [2026-06-28-replay-v2-design.md](../../docs/superpowers/specs/2026-06-28-replay-v2-design.md)
- [FE_PHASE_3_HLD.md](../frontend/docs/FE_PHASE_3_HLD.md)
