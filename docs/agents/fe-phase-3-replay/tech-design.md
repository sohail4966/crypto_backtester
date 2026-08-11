# Tech Design — FE Phase 3: Replay

| Field | Value |
|---|---|
| **Status** | Ready for implementation (Agent B answers incorporated) |
| **PRD** | [prd.md](./prd.md) (Approved) |
| **FE HLD** | [FE_PHASE_3_HLD.md](../../../frontend/docs/FE_PHASE_3_HLD.md) |
| **Backend** | [PHASE_4C_HLD.md](../../../backend/docs/PHASE_4C_HLD.md) — **complete**; consume as-is |
| **OpenAPI** | [openapi.yaml](../../../backend/docs/openapi.yaml) — REST + `x-websocket.replay` |
| **Agent D (backend)** | **No-op** (see §3) — confirmed Agent B |
| **Agent E (frontend)** | Full implementation |
| **Answers** | [answers.md](./answers.md) (Agent B — baked into this doc) |

---

## 1. Architecture Overview

Replay is a **mode on `/`**, not a route. The live chart page keeps symbol / timeframe / indicators; replay overlays a session lifecycle, client clock, and alternate chart data path.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ChartPage (/)                                                             │
│  Topbar: IndicatorsBar + Replay toggle                                    │
│  ChartContainer mode=live|replay                                          │
│  ReplayAnchorBanner (pick_anchor)                                         │
│  ReplayBottomBar (session active)                                         │
└───────────────┬───────────────────────────────┬───────────────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐     ┌─────────────────────────────────────────┐
│ chartStore.replayMode     │     │ replayStore                              │
│ (boolean UX toggle)       │     │ phase · sessionId · cursor · tickQueue   │
└───────────────────────────┘     │ speed · connection · buffer flags        │
                                  └───────────┬─────────────────────────────┘
                                              │
         ┌────────────────────────────────────┼────────────────────────────┐
         ▼                                    ▼                            ▼
┌─────────────────┐              ┌────────────────────┐         ┌──────────────────┐
│ replayApi.ts    │              │ replayWsClient.ts  │         │ useReplayTick    │
│ POST/GET/DELETE │              │ connect · send ·   │         │ setInterval drain│
│ normalize JSON  │              │ typed dispatch     │         │ refill < 20      │
└────────┬────────┘              └─────────┬──────────┘         └────────┬─────────┘
         │                                 │                             │
         ▼                                 ▼                             ▼
   REST /api/v1/replay/*            WS /ws/replay/{id}            series.update /
   (Vite proxy)                     (Vite /ws proxy)              indicator append
```

### Responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| **Browser (client clock)** | `setInterval` at `max(50, 1000 / speed)` ms/bar; local `tickQueue`; play/pause UX; URL `?replaySession=` | Indicator compute, cursor authority |
| **Backend Phase 4c** | Session row + cursor checkpoint; precomputed buffer; O(1) `tick_batch`; seek/extend/indicators | Autoplay loop (removed in 4c) |
| **Chart (replay mode)** | Revealed trail only via `setData` / `update`; pan clamp; follow-cursor (always on) | Ghost bars, equity curve, live chunk manager |

### Data path switch

- **Live (`replayMode` off or phase `inactive`/`pick_anchor` without session):** existing `useChunkManager` → `/chart-data`.
- **Connecting (POST + WS before first snapshot):** keep live `useChunkManager` serving — do not blank the chart.
- **Replay (after first snapshot / session trail authoritative):** `useReplayChart` drives candles + indicator points from `replayStore` (snapshot + drained ticks). Chunk manager is paused / ignored while trail is active.
- **After Stop / teardown:** restore live chunk path once DELETE + WS close + store reset complete.

### Product decisions baked in (§9 PRD)

1. URL write-back `?replaySession=` on create; clear on teardown.
2. Speed = discrete dropdown `0.5 / 1 / 2 / 5 / 10`.
3. Arrow-Right steps one bar when session active.
4. No dedicated post-completed “replay from anchor” button.

---

## 2. Database

### New migrations for v1

**None.** Phase 4c already shipped `V007__replay_sessions.sql` (`app.replay_sessions`: session metadata, cursor, indicators JSONB, speed, state). FE does not introduce tables, columns, or Flyway scripts.

### FE-only persistence

| What | Where | Notes |
|---|---|---|
| Active session id for resume/share | **URL query only** — `?replaySession={uuid}` | `history.replaceState` / React Router search params; clear on teardown / invalid resume |
| Replay mode / phase / queue | In-memory Zustand | Lost on refresh — resume via URL + GET + WS |
| Speed preference mid-session | Server session row + local store | Last `set_speed` / create `speed` |
| Chart prefs (grid, timezone, …) | Existing localStorage | Unchanged |

No `localStorage` key for replay sessions in v1.

---

## 3. Backend

### Verdict for Agent D

**Agent D is a no-op — zero backend code changes for this phase.** Phase 4c is complete (REST sessions + WS v2, OpenAPI `x-websocket`, D-88–D-95). FE consumes the existing contract.

**Contract source of truth (Agent E):** live Phase 4c FastAPI REST handlers + WS code paths first; OpenAPI second (shape/types — casing in OpenAPI can lag). Agent B found **no hard protocol break** requiring Agent D.

Known Phase 4c polish items (`SUPERSEDED` untested, `buffer_loading` mid-batch edge, mixed JSON casing) are handled on the FE via adapters and UX timeouts — do not open Agent D work unless a live smoke test proves a broken protocol path.

### REST surface FE must call

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/replay/sessions` | Create open-ended session |
| `GET` | `/api/v1/replay/sessions/{session_id}` | URL resume / hydrate metadata |
| `DELETE` | `/api/v1/replay/sessions/{session_id}` | Teardown (best-effort) |

### WS surface FE must implement

| Direction | Messages |
|---|---|
| **Client → server** | `play`, `pause`, `step`, `seek`, `set_speed`, `refill`, `set_indicators`, `get_state` |
| **Server → client** | `replay_state`, `snapshot`, `tick_batch`, `buffer_loading`, `buffer_ready`, `buffer_reset`, `replay_completed`, `error` |
| **Close codes** | `4404` unknown session; `4401` superseded (another tab won) |

Path: `WS /ws/replay/{session_id}` (Vite already proxies `/ws` → backend).

### Contract quirks (FE adapter — not Agent D)

Wire JSON is **mixed snake_case / camelCase**. Normalize layer must accept **both** shapes for every aliased field (defensive):

| Surface | Typical live wire | Notes |
|---|---|---|
| Create `201` | snake: `session_id`, `ws_url` | No aliases on response model |
| Create body | snake: `step_timeframe`, `user_id`, … | `ReplaySessionCreate` |
| WS `replay_state` | `model_dump(by_alias=True)`: camel aliases (`startAnchor`, `latestAvailable`, `barIndex`, `queueRemaining`) + unaliased snake (`session_id`, `step_timeframe`, `cursor`, `state`, `speed`) | Authoritative for WS |
| REST GET | Same model; FastAPI may emit aliases — still accept snake fallbacks (`start`, `latest_available`, `bar_index`, `queue_remaining`) | Do not trust OpenAPI casing alone |
| Snapshot / tick_batch / buffer_* | camel (`startAnchor`, `queueRemaining`, `bufferEnd`, …) | As built in engine payloads |

**Fresh-session cursor (verified in engine/buffer):** `cursor_ts` starts **one bar before** `start_anchor`. Initial `snapshot.bars` is **`[]`** (nothing revealed yet). First `step`/`play` tick reveals the clicked anchor bar. PRD “paused at the anchor” = UX ready at that start point, not “anchor already drawn.”

**Decision:** FE types and stores use **camelCase**. `replayApi.ts` + `replayWsClient.ts` normalize inbound payloads (accept both casings) and serialize outbound REST create with snake_case keys. Do not require backend rename for v1.

### Symbol field

`POST` body `symbol` is the trading-pair string FK (`BTC/USDT`), matching `app.symbols.symbol`. FE sends `chartStore.symbol.id` (same value as ticker in current product).

---

## 4. Frontend

### 4.1 File / module plan

```
frontend/src/
  types/replay.ts
  constants/replay.ts                 # speeds, refill threshold, buffer timeout
  services/replayApi.ts               # create / get / delete + normalize
  services/replayWsClient.ts          # WebSocket wrapper
  stores/replayStore.ts               # phase machine + queue + cursor
  stores/chartStore.ts                # + replayMode: boolean
  hooks/useReplaySession.ts           # create / resume / teardown / URL
  hooks/useReplayWs.ts                # events → store
  hooks/useReplayTick.ts              # client clock + refill
  hooks/useReplayChart.ts             # chart data path in replay mode
  hooks/useReplayKeyboard.ts          # Space, ArrowRight, Esc
  components/Replay/ReplayToggle.tsx
  components/Replay/ReplayAnchorBanner.tsx
  components/Replay/ReplayBottomBar.tsx
  components/Replay/ReplayScrubber.tsx
  components/Replay/ReplayStatusPill.tsx
  components/Replay/ReplaySpeedSelect.tsx
  components/Chart/ReplayCandlestickSeries.tsx   # or mode branch in CandlestickSeries
  components/Layout/IndicatorsBar.tsx            # mount ReplayToggle
  pages/ChartPage.tsx                            # banner + bottom bar
  app/App.test.tsx                               # expect Replay present
```

**Not built in v1:** `EquityCurve.tsx`, dedicated `ReplayPage`, sidebar Replay link, ghost-bar series.

Toast: reuse existing `ToastProvider` / `useToast` — no new toast package.

### 4.2 Types (`types/replay.ts`)

```ts
export type ReplayPhase =
  | 'inactive'
  | 'pick_anchor'
  | 'connecting'
  | 'ready'
  | 'playing'
  | 'paused'
  | 'seeking'
  | 'buffer_loading'
  | 'completed'
  | 'error'

export type ReplayConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'amber'
  | 'red'
  | 'closed'

export type ReplaySpeed = 0.5 | 1 | 2 | 5 | 10

export interface ReplayTick {
  bar: OHLCVBar
  indicators: Record<string, { time: number; value: number | null }>
}

export interface ReplaySnapshot {
  bars: OHLCVBar[]
  indicators: IndicatorSeriesMap
  cursor: number | null
  startAnchor: number
  latestAvailable: number | null
}

export interface ReplaySessionMeta {
  sessionId: string
  symbol: string
  timeframe: string
  stepTimeframe: string
  startAnchor: number
  latestAvailable: number | null
  cursor: number | null
  serverState: 'idle' | 'playing' | 'paused' | 'completed'
  speed: number
  barIndex: number
  queueRemaining: number
  indicators: IndicatorSpec[]
}

// Discriminated unions for WS inbound / outbound (mirror OpenAPI oneOf)
```

### 4.3 Constants

```ts
export const REPLAY_SPEEDS: ReplaySpeed[] = [0.5, 1, 2, 5, 10]
export const REPLAY_REFILL_THRESHOLD = 20          // match backend default
export const REPLAY_BASE_INTERVAL_MS = 1000
export const REPLAY_MIN_INTERVAL_MS = 50
export const REPLAY_BUFFER_UI_TIMEOUT_MS = 3000
export const REPLAY_SESSION_QUERY = 'replaySession'
```

Interval: `Math.max(REPLAY_MIN_INTERVAL_MS, REPLAY_BASE_INTERVAL_MS / speed)`.

### 4.4 Stores

#### `chartStore` (+ `replayMode`)

```ts
replayMode: boolean
setReplayMode: (on: boolean) => void
```

- Toggle on → if no session: `replayStore.enterPickAnchor()`; set `replayMode true`.
- Toggle off → teardown session if any; `replayStore.reset()`; `replayMode false` → `inactive`.
- Stop button → teardown session; keep `replayMode true` → `pick_anchor`.

Keep `replayMode` separate from phase so symbol/TF change can teardown session while mode stays on (`pick_anchor`).

#### `replayStore`

State (conceptual):

| Field | Role |
|---|---|
| `phase` | Client state machine (§5) |
| `sessionId` | Active UUID or null |
| `wsUrl` | Relative path from create |
| `meta` | Cursor, anchors, latestAvailable, serverState, … |
| `tickQueue` | `ReplayTick[]` |
| `trailBars` / `trailIndicators` | Last applied snapshot + applied ticks (source of truth for chart) |
| `speed` | Selected dropdown speed |
| `followReplay` | Always `true` in v1 — no UI toggle |
| `connection` | `ReplayConnectionStatus` + optional reason (`superseded` \| `not_found` \| `error`) |
| `bufferLoadingSince` | For 3s UI timeout |
| `phaseBeforeBuffer` | Prior `playing`/`paused` to restore on buffer timeout |
| `errorMessage` | Last unrecoverable / toast-driven error |

Actions: `enterPickAnchor`, `beginConnect`, `applyReplayState`, `applySnapshot`, `enqueueTicks`, `drainOne`, `setPhase`, `setSpeed`, `setConnection`, `clearQueue`, `reset`, etc.

### 4.5 Hooks

| Hook | Responsibility |
|---|---|
| `useReplaySession` | Orchestrate create on bar click; URL resume on mount; DELETE + close on stop / toggle off / symbol·TF change; sync `?replaySession=` |
| `useReplayWs` | Own `ReplayWsClient` lifecycle; map events → store; handle close 4401/4404 |
| `useReplayTick` | While `playing`: interval drain; call chart apply; send `refill` when `tickQueue.length < 20`; stop on pause/completed/teardown |
| `useReplayChart` | When trail authoritative: feed trail into candle/indicator series; disable chunk prefetch; clamp pan to oldest revealed; follow cursor (`followReplay` always on) |
| `useReplayKeyboard` | Window-level Space play/pause; ArrowRight step (`count: 1`); Esc only in `pick_anchor` → inactive + `replayMode` off (Esc always wins in pick_anchor for v1) |

Wire hooks from `ChartPage` (session/banner/bar/keyboard) and `ChartContainer` (chart path / click-for-anchor).

### 4.6 API / WS clients

#### `replayApi.ts`

- `createReplaySession(body)` → normalize `{ sessionId, wsUrl }`
- `getReplaySession(id)` → `ReplaySessionMeta`
- `deleteReplaySession(id)` → void; swallow 404
- Create payload (wire):

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "indicators": [{ "key": "RSI", "params": { "period": 14 }, "pane": "subchart" }],
  "speed": 1.0,
  "autoplay": false
}
```

`indicators` = visible specs from `indicatorStore`, same rules as `ChartContainer` today:

1. Include only actives with `visible !== false`.
2. Include `pane` (`overlay` | `subchart`) on every spec.
3. **Dedupe** by `key + JSON.stringify(params) + pane` — identical specs once; distinct params/panes all sent.
4. Omit `step_timeframe` (defaults to timeframe).

Same rules for mid-session WS `set_indicators`.

#### `replayWsClient.ts`

- `connect(wsUrl)` — resolve absolute URL: if `wsUrl` starts with `/`, use `ws(s)://{location.host}{wsUrl}` (Vite proxy).
- `send(cmd)`, `close()`, event callbacks / async iterator.
- Parse JSON; normalize keys; dispatch by `type`.
- On unexpected close: surface code/reason to store.

### 4.7 UI components

| Component | Behavior |
|---|---|
| `ReplayToggle` | Button label “Replay”; pressed style when `replayMode`; beside `+ Add indicator` in `IndicatorsBar` |
| `ReplayAnchorBanner` | “Click a bar to start replay”; visible in `pick_anchor` |
| `ReplayBottomBar` | Play / pause / **stop** / step / speed select / scrubber / status pill / connection dot; mount for connecting→completed (and seeking/buffer_loading) |
| `ReplaySpeedSelect` | Native `<select>` or styled list: 0.5× … 10× |
| `ReplayScrubber` | Progress `(cursor − startAnchor) / (latestAvailable − startAnchor)`; tooltip (D-95); seek on release. If `latestAvailable` null or denom ≤ 0 → **disabled empty track at 0%**. At completed (`cursor === latestAvailable`) → **100%**. After seek earlier from completed → phase `paused`, Play re-enabled |
| `ReplayStatusPill` | Buffer loading; completed badge; clear loading on `buffer_ready` **or** 3s timeout (timeout also restores phase — see §5) |
| Connection dot | **Green** `open`; **amber** 4401/4404; **red** unrecoverable / `error` phase; idle/`closed` = no alarm |

### 4.8 Chart integration

1. **`mode`:** `ChartContainer` reads `replayMode` + active `sessionId` / phase. Keep live `useChunkManager` through `connecting`; when first snapshot makes trail authoritative, skip live chunk updates. After teardown, resume live path.
2. **Anchor click:** In `pick_anchor` only, `chart.subscribeClick` → resolve clicked bar unix `time` (prefer bar under click; crosshair time fallback) → create session. **Ignore clicks outside `pick_anchor`.**
3. **Revealed trail:** First snapshot often has **`bars: []`** (cursor one bar before anchor) → `setData([])`. Each drained **or immediately-applied step** tick → `candlestickSeries.update(bar)` + append indicator points.
4. **Out-of-window seek / `buffer_reset`:** Clear queue; replace trail from new snapshot (`setData`).
5. **In-window seek (`reloaded=false`):** No snapshot — **slice** existing `trailBars` / indicator points to `time <= newCursor`; apply `replay_state` cursor/meta. Not a bug.
6. **Pan clamp (D-90):** Logical range min ≥ oldest revealed bar (no-op while trail empty).
7. **Follow cursor:** Always on in v1 — on tick, scroll so cursor stays in view.
8. **No ghosts / no equity pane.**

### 4.9 Keyboard

| Key | When | Action |
|---|---|---|
| `Space` | Session active; focus not in `input` / `textarea` / `contenteditable` / `<select>` | Toggle play/pause; `preventDefault` (window-level, including when focus on bottom-bar buttons) |
| `ArrowRight` | Same focus rules; session active | `{ action: "step", count: 1 }`; **apply returned ticks immediately** to trail (paused or playing); do not double-enqueue for interval drain |
| `Esc` | `pick_anchor` only | Phase `inactive`, `replayMode` false — **always wins in pick_anchor for v1** (drawing-tool Esc deferred) |

### 4.10 URL sync

| Event | URL |
|---|---|
| Successful `POST` create | `replace` search with `replaySession={sessionId}` |
| Successful URL resume | Keep param |
| Teardown (stop, toggle off, invalid GET, 4404 cleanup) | Remove `replaySession` |
| Landing `/?replaySession=` | `GET` → if 404 toast + clear param + stay live; if ok open WS, skip pick_anchor, `replayMode=true`, phase `paused` or `completed` from state |

Do not invent `/replay` routes. Unknown paths already redirect to `/`.

### 4.11 Mid-session side effects

| Trigger | Behavior |
|---|---|
| Visible indicators change | Optimistic pause → WS `set_indicators` (visible+pane+deduped) → expect `buffer_reset` + `snapshot` → force local `paused`, stop clock, **send `{ action: "pause" }`** to resync server (backend may flip `playing` without a batch) → remain paused until user Play |
| Symbol or timeframe change | DELETE + close WS; if `replayMode` → `pick_anchor`; else inactive; clear URL param |
| **Stop** (button) | Pause + DELETE + close → **`pick_anchor` with `replayMode` still on**; restore live chart path |
| Toggle off | Same teardown as stop + **`replayMode` false** → `inactive` |

---

## 5. State Machine

```
                    ┌──────────────┐
         toggle on  │   inactive   │  toggle off / Esc (from pick)
                 ┌─►│ replayMode 0 │◄────────────────────────────┐
                 │  └──────┬───────┘                             │
                 │         │ toggle on                           │
                 │         ▼                                     │
                 │  ┌──────────────┐                             │
                 │  │ pick_anchor  │◄── symbol/TF teardown ──┐   │
                 │  └──────┬───────┘    (mode still on)      │   │
                 │         │ bar click / URL resume          │   │
                 │         ▼                                 │   │
                 │  ┌──────────────┐                         │   │
                 │  │ connecting   │── error ──► error ──────┼───┤
                 │  └──────┬───────┘                         │   │
                 │         │ replay_state + snapshot         │   │
                 │         ▼                                 │   │
                 │  ┌──────────────┐   play    ┌──────────┐  │   │
                 │  │   paused     │◄─────────►│ playing  │  │   │
                 │  │ (was ready)  │   pause   └────┬─────┘  │   │
                 │  └──────┬───────┘                │        │   │
                 │         │                        │        │   │
                 │         │ seek oob prefetch      │ extend │   │
                 │         ▼                        ▼        │   │
                 │  ┌──────────────┐         ┌──────────────┐│   │
                 │  │   seeking    │         │buffer_loading││   │
                 │  └──────┬───────┘         └──────┬───────┘│   │
                 │         │ snapshot               │ ready /││   │
                 │         │                        │ 3s TO  ││   │
                 │         └───────────┬────────────┘        │   │
                 │                     ▼                     │   │
                 │              ┌──────────────┐             │   │
                 │              │  completed   │ play disabled│   │
                 │              └──────┬───────┘             │   │
                 │                     │ stop → pick_anchor │   │
                 │                     │ toggle → inactive  │   │
                 └─────────────────────┴─────────────────────┘   │
                                                                 │
                    error (unrecoverable) → toast → pick_anchor or inactive
```

### Phase notes

| Phase | Entry | Exit |
|---|---|---|
| `inactive` | Mode off or Esc from pick | Toggle on → pick_anchor |
| `pick_anchor` | Mode on, no session; **Stop** after teardown | Bar click → connecting; Esc → inactive |
| `connecting` | POST and/or WS open (live chart still shown) | Snapshot → **paused**; fail → error |
| `ready` | Type retained for HLD; **store sets `paused` on first snapshot** (no distinct ready UI) | — |
| `playing` | Client clock running | Pause / seek / buffer / completed / stop |
| `paused` | First snapshot, user pause, optimistic indicator pause, seek done, buffer timeout restore, seek-back from completed | Play / step / seek / stop |
| `seeking` | Scrub needs reload | New snapshot → paused |
| `buffer_loading` | `buffer_loading` event (remember prior playing/paused) | `buffer_ready` → prior phase; **3s timeout → clear pill + restore prior phase** (do not stay stuck) |
| `completed` | `replay_completed` | Scrub earlier → **paused + Play enabled**; Stop → pick_anchor; toggle off → inactive |
| `error` | Unrecoverable (connection **red**) | Transition to pick_anchor (mode on) or inactive |

Server `state` (`idle`/`playing`/`paused`/`completed`) is mirrored in `meta` but **UI phase** is client-authoritative for clock and chrome. After `set_indicators`, ignore server `playing` until user Play (and send WS `pause`).

---

## 6. API Contract

### 6.1 REST — create

`POST /api/v1/replay/sessions`

**Request (wire):**

```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start": 1704067200,
  "indicators": [
    { "key": "EMA", "params": { "period": 20 }, "pane": "overlay" }
  ],
  "speed": 1.0,
  "autoplay": false
}
```

**Response `201` (wire):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "ws_url": "/ws/replay/550e8400-e29b-41d4-a716-446655440000"
}
```

**Normalized FE:** `{ sessionId, wsUrl }`.

### 6.2 REST — get / delete

`GET /api/v1/replay/sessions/{session_id}` → session snapshot (normalize to `ReplaySessionMeta`).  
`DELETE` → `204`; treat `404` as success during teardown.

### 6.3 WS — connect handshake

On open, server sends (order):

1. `replay_state`
2. `snapshot`

Example `replay_state` (fresh session — cursor **before** anchor):

```json
{
  "type": "replay_state",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "step_timeframe": "1h",
  "startAnchor": 1704067200,
  "latestAvailable": 1706745600,
  "cursor": 1704063600,
  "state": "paused",
  "speed": 1.0,
  "barIndex": 0,
  "queueRemaining": 100,
  "indicators": [{ "key": "EMA", "params": { "period": 20 }, "pane": "overlay" }]
}
```

Example `snapshot` (fresh — **no bars revealed yet**):

```json
{
  "type": "snapshot",
  "bars": [],
  "indicators": {},
  "cursor": 1704063600,
  "startAnchor": 1704067200,
  "latestAvailable": 1706745600
}
```

First `{ "action": "step", "count": 1 }` (or first play drain) reveals the anchor bar via `tick_batch`.
### 6.4 WS — client commands

```json
{ "action": "play", "speed": 2 }
{ "action": "pause" }
{ "action": "step", "count": 1 }
{ "action": "seek", "to": 1704153600 }
{ "action": "set_speed", "speed": 5 }
{ "action": "refill" }
{ "action": "set_indicators", "indicators": [{ "key": "RSI", "params": { "period": 14 }, "pane": "subchart" }] }
{ "action": "get_state" }
```

### 6.5 WS — server events (playback)

`tick_batch`:

```json
{
  "type": "tick_batch",
  "ticks": [
    {
      "bar": { "time": 1704153600, "open": 42200, "high": 42600, "low": 42100, "close": 42500, "volume": 90 },
      "indicators": { "EMA_20": { "time": 1704153600, "value": 42250 } }
    }
  ],
  "cursor": 1704153600,
  "queueRemaining": 87
}
```

Others:

```json
{ "type": "buffer_loading" }
{ "type": "buffer_ready", "bufferEnd": 1705000000, "latestAvailable": 1706745600 }
{ "type": "buffer_reset" }
{ "type": "replay_completed" }
{ "type": "error", "code": "SEEK_OUT_OF_RANGE", "message": "..." }
```

### 6.6 Control → protocol mapping

| UI | Protocol / local |
|---|---|
| Play | `{ action: "play", speed }` + start interval |
| Pause | `{ action: "pause" }` + stop interval |
| Stop | pause + `DELETE` + close WS → **`pick_anchor`** (`replayMode` on) |
| Toggle off | Stop teardown + `replayMode` false → `inactive` |
| Step → / ArrowRight | `{ action: "step", count: 1 }` — **always `count: 1`**; apply `tick_batch` ticks **immediately** |
| Speed dropdown | `{ action: "set_speed", speed }` (+ update local interval if playing) |
| Scrubber (in-window) | `{ action: "seek", to }` → `replay_state` only → **slice trail locally** |
| Scrubber (oob) | seek → `buffer_reset` + `snapshot` replace |
| Hidden refill | `{ action: "refill" }` when queue `< 20` |

---

## 7. Testing Plan

### Unit — `replayStore`

- Phase transitions: pick_anchor → connecting → **paused** → playing → paused → completed.
- Fresh snapshot with empty bars / cursor before anchor; first drain/step reveals anchor.
- `enqueueTicks` / `drainOne` queue semantics; refill threshold flag; step path applies immediately without double-drain.
- In-window seek slices trail; snapshot replace clears queue and rebuilds trail.
- `SEEK_OUT_OF_RANGE` path does not move cursor; connection/error flags set correctly.
- Buffer timeout restores prior phase + clears pill.
- `reset()` clears session fields.

### Unit — `replayApi` normalize

- Maps `session_id`/`ws_url` → camelCase.
- Tolerates **both** snake and camel for GET/state fields (`start` / `startAnchor`, `bar_index` / `barIndex`, …).

### Unit / integration — `replayWsClient` (mock WebSocket)

- Prefer injectable transport or stub `global.WebSocket` with Vitest `vi.fn` (repo pattern). **No MSW required.**
- Dispatches typed events; send serializes actions.
- Close `4404` / `4401` invoke handlers with amber semantics.
- Connect builds `ws://` URL from relative `ws_url`.

### Hook tests

- `useReplayTick`: advances one bar per interval; sends refill below threshold; stops when paused.
- `useReplaySession`: create writes URL param; teardown clears it; invalid resume toasts + clears; Stop → pick_anchor with mode on.

### App / component tests

- **Flip** `App.test.tsx`: `getByRole('button', { name: 'Replay' })` **is** present; still no “Indicators” label; no sidebar Replay nav.
- **Mock replay hooks/WS by default** in App / ChartContainer RTL tests so existing chart tests stay offline.
- Dedicated replay unit/hook tests exercise real store + WS client with fixtures.
- `ReplayBottomBar`: play/pause/stop/step/speed callbacks fire.
- `ReplayScrubber`: progress math with moving `latestAvailable`; null/zero-denom → 0% disabled; tooltip present.
- Optional: ChartPage banner visible in pick_anchor (light RTL).

### Manual smoke (Agent E / QA)

- Create → play → pause → scrub → stop against local Phase 4c API.
- Second tab supersede (4401).
- Resume via pasted `?replaySession=`.

### Quality gate

`npm run build` and `npm test` must pass (AC-14).

---

## 8. Implementation Order

### Agent D — Backend

| Task | Notes |
|---|---|
| **D0 — No-op** | Agent B confirmed: **no code changes**. Phase 4c already deployed; FE normalize absorbs casing |
| D1 (only if smoke breaks) | Minimal contract fix — prefer documenting + FE normalize over drive-by refactors |

**Default: Agent D skips; Agent E starts immediately. Agent D work = no.**

### Agent E — Frontend (sequenced)

| # | Task | Depends |
|---|---|---|
| E1 | `types/replay.ts`, `constants/replay.ts` | — |
| E2 | `replayApi.ts` + unit tests (normalize) | E1 |
| E3 | `replayWsClient.ts` + mock WS tests | E1 |
| E4 | `replayStore.ts` + phase/queue unit tests | E1 |
| E5 | `chartStore.replayMode` | — |
| E6 | `useReplaySession` + URL sync | E2–E5 |
| E7 | `useReplayWs` wire events → store | E3, E4, E6 |
| E8 | `useReplayTick` client clock + refill | E4, E7 |
| E9 | UI: `ReplayToggle`, banner, bottom bar, speed, scrubber, status pill | E4, E5 |
| E10 | Chart path: `useReplayChart`, trail setData/update, pan clamp, follow cursor, anchor click | E6–E8 |
| E11 | Indicator mid-session → `set_indicators`; symbol/TF teardown → pick_anchor | E6, E10 |
| E12 | `useReplayKeyboard` (Space, ArrowRight, Esc) | E8, E9 |
| E13 | Toasts for SEEK_OUT_OF_RANGE, 4401, 4404, generic errors | E7, E9 |
| E14 | Flip `App.test`; component tests; full `npm test` + `npm run build` | E9+ |

Suggested PR slices: (1) types+api+ws+store, (2) session hooks+URL, (3) UI chrome, (4) chart integration+keyboard+tests.

---

## 9. Risks / Edge Cases

| Risk | Mitigation |
|---|---|
| Mixed snake/camel JSON | Single normalize layer accepts **both**; never read wire keys in UI; live code > OpenAPI for casing |
| Fresh empty snapshot | Expect `bars: []`; first tick reveals anchor — do not invent ghost anchor candle |
| In-window seek no snapshot | Slice trail locally from `replay_state` cursor |
| Step while playing | Apply step ticks immediately; exclude from interval drain to avoid double-apply; always `count: 1` |
| `set_indicators` restores server playing | Client phase authoritative; send WS `pause` after snapshot |
| `ws_url` relative path | Build absolute WS URL via `location.host` + Vite `/ws` proxy |
| Stuck `buffer_loading` UI | 3s timeout clears pill **and** restores prior playing/paused phase |
| Seek out of range | Toast; snap scrubber to last valid `cursor` |
| Concurrent tab (4401) | Amber connection; pause clock; message “Opened in another tab” |
| Unknown session (4404) | Toast; amber; offer re-pick; clear URL |
| Unrecoverable errors | Red connection dot + toast; pick_anchor or inactive |
| Completed at latest candle | Badge; disable play; scrub back → paused + Play on; no “replay from anchor” button |
| Scrubber null / zero denom | Disabled track at 0%; completed → 100% |
| Symbol id vs ticker | Send `symbol.id` (`BTC/USDT`); matches backend FK |
| Live vs replay data fight | Live through connecting; gate chunk manager only after first snapshot; restore after teardown |
| Indicator series id mismatch | Use backend map keys from snapshot/ticks (`EMA_20`, …) aligned with `indicatorStore.seriesId`; specs include `pane`, visible-only, deduped |
| Queue underrun while playing | Refill early (`< 20`); if empty, stay in playing but wait for batch (optional brief stall) |
| DELETE fails on stop | Best-effort; still close WS and reset local state → pick_anchor |
| Refresh mid-play | URL resume restores paused/completed from DB cursor — not mid-queue (acceptable) |
| Esc vs drawings | Esc always wins in pick_anchor for v1; don’t steal Esc outside pick_anchor |

---

## 10. Out of Scope (reminder)

- Equity curve sub-pane  
- Ghost / dim warmup or future bars  
- Signals / trades / patterns on replay ticks  
- Auth / user-owned sessions  
- `/replay` product page  
- Multi-chart replay sync  
- Backend protocol redesign  

---

## 11. References

- [prd.md](./prd.md) — approved requirements + §9 decisions  
- [answers.md](./answers.md) — Agent B Q&A (incorporated here)  
- [FE_PHASE_3_HLD.md](../../../frontend/docs/FE_PHASE_3_HLD.md)  
- [SPEC-001.md](../../../frontend/docs/SPEC-001.md) §4.5, §8.3  
- [PHASE_4C_HLD.md](../../../backend/docs/PHASE_4C_HLD.md)  
- [openapi.yaml](../../../backend/docs/openapi.yaml) — REST + `x-websocket.replay`  
- [DECISIONS.md](../../../backend/docs/DECISIONS.md) — D-69, D-88–D-95  
- Live code: `backend/api/schemas/replay.py`, `backend/api/ws/replay.py`, `backend/api/services/replay_engine.py`, `backend/api/services/replay_buffer.py`  
