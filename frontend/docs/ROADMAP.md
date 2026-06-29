# Frontend Roadmap — TradingView-Style Chart Client

## Vision

A browser-based chart client that renders market data, indicators, drawings, and replay
playback — with **zero compute in the browser**. The frontend fetches aligned payloads
from the Python API, manages windowed memory, and owns only interaction state (scroll,
zoom, replay timing, layout).

The authoritative architecture spec is **[SPEC-001](SPEC-001.md)** (v2.0). This roadmap
sequences implementation, records status, and maps each frontend phase to backend
dependencies — mirroring [backend/docs/ROADMAP.md](../../backend/docs/ROADMAP.md).

---

## Relationship to Backend

| Backend phase | What it unlocks for the frontend |
|---|---|
| [Phase 4](../../backend/docs/PHASE_4_HLD.md) | Symbols, candles, indicators, users, watchlists, replay WS |
| [Phase 4b](../../backend/docs/PHASE_4B_HLD.md) ✅ | **`GET /chart-data`**, symbol v2 (**D-81**, **D-86**) |
| [Phase 4c](../../backend/docs/PHASE_4C_HLD.md) ✅ **8.9/10** | **Replay V2** — WS streaming, rolling buffer (**D-88–D-95**) |
| Phase 4d (planned) | Backtest HTTP API, non-empty `signals` / `trades` in chart-data |
| Phase 4d (planned) | Workspace sync (`GET/POST /workspace`) for drawings + layouts (**D-85**) |
| Phase 11 (planned) | JWT auth, live candle WebSocket for watchlist ticks (**D-78**) |

**OpenAPI:** [backend/docs/openapi.yaml](../../backend/docs/openapi.yaml) (v0.4.1)  
**Decisions:** [backend/docs/DECISIONS.md](../../backend/docs/DECISIONS.md) — D-80–D-95

---

## Technology Stack (locked in SPEC-001 §2)

| Concern | Choice |
|---|---|
| Framework | React 18 + TypeScript |
| Charting | lightweight-charts v4 |
| State | Zustand (slice per domain) |
| Data fetching | TanStack Query v5 |
| Routing | React Router v6 |
| Styling | Tailwind + CSS variables |
| Local cache | IndexedDB (`idb-keyval`) |
| Build / test | Vite, Vitest, React Testing Library |

---

## Phase 0 — Project Scaffold

**Status:** Complete — [FE_PHASE_0_HLD.md](FE_PHASE_0_HLD.md)  
**Design doc:** [FE_PHASE_0_HLD.md](FE_PHASE_0_HLD.md)  
**Prerequisite:** Node 20+, backend running locally (`python -m api`)

**Theme:** Empty shell that builds, routes, and proxies to the API — no chart yet.

**Goal:** `npm run dev` serves a dark-themed app shell; `npm run build` and `npm test` pass.

| Area | What gets built |
|---|---|
| Tooling | Vite + TS + Tailwind + path aliases |
| App shell | `App.tsx`, `QueryProvider`, `ThemeProvider`, React Router (`/`, `/replay`, `/backtest`) |
| API client | `services/api.ts` typed wrapper over OpenAPI paths |
| Proxy | Vite dev proxy `/api` → `localhost:8000` |

**Done when:** Three routes render placeholder pages inside `AppShell`; health check
against `GET /api/v1/meta/health` succeeds from the browser.

---

## Phase 1 — Core Chart

**Status:** Complete — [FE_PHASE_1_HLD.md](FE_PHASE_1_HLD.md)  
**Design doc:** [FE_PHASE_1_HLD.md](FE_PHASE_1_HLD.md) · **Spec:** [SPEC-001 §4–5, §10](SPEC-001.md)  
**Prerequisite:** [Phase 4b](../../backend/docs/PHASE_4B_HLD.md) complete ✅  
**Backend:** `GET /chart-data`, `GET /symbols/search`, `GET /symbols/{id}/data-range`

**Theme:** Candlestick + volume chart with windowed loading and symbol switching.

**Goal:** User opens `/`, sees BTC/USDT candles anchored on **stored data range** (not
wall-clock `now`), can switch symbol and timeframe.

| Area | What gets built |
|---|---|
| Types | `Symbol`, `ChartDataResponse`, `OHLCVBar` |
| Data | `fetchChartData` → `GET /chart-data`; `getCandleDataRange` → metadata endpoint |
| Windowing | `chunkManager` + `useChunkManager` — 500-bar chunks, scroll-back prefetch (**D-82**) |
| Chart | `ChartContainer`, `CandlestickSeries`, `VolumeSeries`, `ChartContext` |
| State | `chartStore` — symbol entity, timeframe, active pane |
| UI | `SymbolSearch`, timeframe selector, `Topbar`, `Sidebar` (minimal) |

**Key engineering challenges:**

- Anchor initial window on `data-range.latest`, not `Date.now()` (DB may lag).
- Resolve CSS theme tokens to hex before passing colors to lightweight-charts.
- Stabilise chart `useEffect` deps — do not recreate lw-charts instance on handler identity changes.

**Done when:** Chart loads 500 bars for BTC/USDT `1h` and SOL/USDT `1m`; symbol switch
refetches; scroll-back prefetches prior chunk without blanking the chart.

---

## Phase 2 — Indicators

**Status:** Complete for chart indicators; live backend smoke testing still recommended  
**Design doc:** [FE_PHASE_2_HLD.md](FE_PHASE_2_HLD.md) · **Spec:** [SPEC-001 §5.2](SPEC-001.md)  
**Prerequisite:** FE Phase 1 complete  
**Backend:** `GET /chart-data?indicators=…`, `GET /indicators` catalog

**Theme:** Overlay and sub-chart indicators from the unified response — never computed
in the browser.

**Goal:** User adds RSI / EMA from the catalog; series render aligned to candles.

| Area | What gets built |
|---|---|
| State | `indicatorStore` — active configs, visibility, settings, bundled indicators |
| UI | `IndicatorPanel`, `IndicatorSettingsDialog`, indicator tabs/chips |
| Chart | `OverlayIndicatorSeries` (main pane), `IndicatorSubPane` (synced oscillator panes) |
| Integration | Indicator specs serialised into `chart-data` query; map keys e.g. `RSI_14` |
| Hardening | ESLint quality gate, lifecycle tests, stale-prefetch guard, no indicator-triggered viewport reset |

**Done when:** Adding EMA(20) overlay and RSI(14) sub-chart updates chart without separate
candle/indicator requests; toggling off hides series.

---

## Phase 3 — Replay

**Status:** Not started — **current focus**  
**Design doc:** [FE_PHASE_3_HLD.md](FE_PHASE_3_HLD.md) · **Spec:** [SPEC-001 §4.5](SPEC-001.md)  
**Prerequisite:** FE Phase 1–2 complete  
**Backend:** ✅ [Phase 4c](../../backend/docs/PHASE_4C_HLD.md) complete — **8.9/10** ([assessment](../../backend/docs/PHASE_4C_HLD.md#phase-4c-completion-assessment)); `POST /replay/sessions`, `WS /ws/replay/{sessionId}`  
**Decisions:** **D-88–D-95** — WebSocket tick batches; client-owned playback clock

**Theme:** Browser owns playback clock; backend precomputes indicators in a rolling buffer.

**Goal:** `/replay` progressively reveals bars; play/pause/step/speed/jump work.

| Area | What gets built |
|---|---|
| State | `replayStore` — state machine, tick queue, `revealedBars` |
| Engine | `useReplayWs` + `useReplayTick` — WS refill + `setInterval` |
| UI | `ReplayToolbar`, `SpeedControl`, `DateSelector`, `EquityCurve` (stub) |
| Chart | `ChartContainer` replay mode — `series.update()` per tick |

**Done when:** Replay streams bars via WS with tick-batch refill; Space toggles play/pause;
step-forward advances one bar; jump-to-date sends seek and resets from snapshot.

---

## Phase 4 — Watchlist + Symbol Search

**Status:** Not started  
**Design doc:** [FE_PHASE_4_HLD.md](FE_PHASE_4_HLD.md) · **Spec:** [SPEC-001 §5, §8.1](SPEC-001.md)  
**Prerequisite:** FE Phase 1 complete  
**Backend:** `POST /users`, `GET/POST …/watchlists`, `GET /symbols/search`

**Theme:** Persistent watchlists scoped by `user_id`; symbol entities everywhere.

**Goal:** Default watchlist loads on boot; clicking a row switches the active chart symbol.

| Area | What gets built |
|---|---|
| Bootstrap | `ensureUserId()` — `localStorage` + `POST /users` |
| State | `watchlistStore` + IndexedDB cache under backend-primary model (**D-85** interim: local cache only) |
| UI | `WatchlistPanel`, `WatchlistRow`, enhanced `SymbolSearch` |
| Prices | Placeholder `—` until Phase 11 live WS; optional poll last bar close |

**Done when:** App creates/reuses a dev user; watchlist syncs from API; row click updates
`chartStore.symbol`; add-to-watchlist works.

---

## Phase 5 — Drawings (MVP)

**Status:** Not started  
**Design doc:** [FE_PHASE_5_HLD.md](FE_PHASE_5_HLD.md) · **Spec:** [SPEC-001 §5.5–5.6](SPEC-001.md)  
**Prerequisite:** FE Phase 1 complete  
**Backend:** None required for render; **Phase 4d** for server sync (**D-83**, **D-84**, **D-85**)

**Theme:** Five drawing tools; Price Range as first-class primitive.

**Goal:** User places trend lines, horizontal lines, rectangles, price ranges, and text
notes; drawings persist per symbol+timeframe in IndexedDB.

| Area | What gets built |
|---|---|
| Types | `Drawing` union — see SPEC-001 §5.5 |
| State | `drawingStore` + IndexedDB |
| UI | `DrawingToolbar`, click-to-place via `chart.subscribeClick` |
| Render | `DrawingsLayer` — lw-charts price lines / line series |
| Shortcuts | `D/H/R/P/T`, `Esc`, `Delete` via `useKeyboardShortcuts` |

**Explicitly excluded (SPEC-002):** Fibonacci, channels, rays, pattern tools.

**Done when:** All five tools create, render, and survive page reload; colors are resolved
hex (not CSS `var()` strings).

---

## Phase 6 — Multi-Chart + Workspace Polish

**Status:** Not started  
**Design doc:** [FE_PHASE_6_HLD.md](FE_PHASE_6_HLD.md) · **Spec:** [SPEC-001 §5.4, §8.2–8.3](SPEC-001.md)  
**Prerequisite:** FE Phases 1–5 complete  
**Backend:** Phase 4d for full workspace sync; interim IndexedDB only

**Theme:** Multi-pane layouts with configurable sync; workspace persistence.

**Goal:** User switches 1×1 / 1×2 / 2×2 / 1+2 layouts; crosshair and visible-range sync
across panes; theme toggle persists.

| Area | What gets built |
|---|---|
| Layout | `MultiChartLayout`, per-pane symbol/timeframe in `workspaceStore` |
| Sync | `syncStore`, `useMultiChartSync`, `SyncConfigPanel` (**D-87**) |
| Workspace | `workspaceStorage` — theme, layouts; debounced persist (`Ctrl+S`) |
| Theme | Light/dark via CSS variables + `ThemeProvider` |

**Done when:** 2×2 shows four independent charts; sync toggles work; layout + theme survive
reload from IndexedDB.

---

## Post-MVP Frontend Work (Future Specs)

| Feature | Spec | Backend dependency |
|---|---|---|
| Fibonacci + advanced drawings | SPEC-002 | Phase 4d workspace |
| Backtest results UI | SPEC-003 (TBD) | Phase 4d backtest API |
| Alert UI | SPEC-006 | Phase 8 screener |
| Auth + login | SPEC-008 | Phase 11 JWT |
| Mobile layout | SPEC-009 | — |
| Replay WebSocket streaming | SPEC-010 | Phase 11 perf path |
| Live watchlist ticks | SPEC-001 §13.2 | Phase 11 WS |

---

## Implementation Order

```
Phase 0 (scaffold)
    └── Phase 1 (core chart) ──┬── Phase 2 (indicators)
                               ├── Phase 4 (watchlist)     [parallel after Phase 1]
                               └── Phase 5 (drawings)      [parallel after Phase 1]
    Phase 2 + Phase 1 ──► Phase 3 (replay)                 [current focus]
    Phases 1–5 ──► Phase 6 (multi-chart + workspace)
```

Phases 2, 4, and 5 can run in parallel once Phase 1 lands. Phase 3 (replay) needs
indicators in chart-data requests. Phase 6 integrates everything.

---

## Backend Gate Checklist (before starting)

| FE phase | Required backend |
|---|---|
| 0 | `GET /meta/health` |
| 1 | Phase 4b: `/chart-data`, `/symbols/search`, `/symbols/{id}/data-range` |
| 2 | + `/indicators` catalog |
| 3 | + `/replay/sessions`, `WS /ws/replay/{id}` — ✅ [Phase 4c](../../backend/docs/PHASE_4C_HLD.md) **8.9/10** |
| 4 | + `/users`, `/users/{id}/watchlists` |
| 5 | — (IndexedDB only) |
| 6 | — (4d optional for server workspace) |

---

## Related Docs

| Doc | Purpose |
|---|---|
| [SPEC-001.md](SPEC-001.md) | Full architecture, types, components, API contracts |
| [FE_PHASE_*_HLD.md](FE_PHASE_0_HLD.md) | Per-phase implementation guides |
| [backend/docs/PHASE_4B_HLD.md](../../backend/docs/PHASE_4B_HLD.md) | Chart-data + replay chunk API |
| [backend/docs/PHASE_4B_FE_GAPS.md](../../backend/docs/PHASE_4B_FE_GAPS.md) | Backend fixes for derived timeframe metadata |
| [backend/docs/openapi.yaml](../../backend/docs/openapi.yaml) | REST contract source of truth |
| [backend/docs/DECISIONS.md](../../backend/docs/DECISIONS.md) | D-80–D-87 frontend architecture |
