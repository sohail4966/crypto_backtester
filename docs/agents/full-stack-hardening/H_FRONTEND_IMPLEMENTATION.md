# Agent H — Frontend Implementation Report

**Scope:** Recommended solutions for FE-001 … FE-018 (Waves 1–4)  
**Sources:** `E_FRONTEND_SOLUTIONS.md`, `C_SEVERITY_DEPENDENCY.md`, `B_FRONTEND_ISSUES.md`, `D_BACKEND_SOLUTIONS.md`  
**Constraint:** `frontend/` only (backend contracts assumed from Agent F / D).

---

## Verification

| Command | Result |
|---|---|
| `npm test` (frontend) | **170 passed** (43 files) |
| `npm run build` (`tsc -b && vite build`) | **OK** |

---

## Per-issue summary

### FE-001 — API client drops backend error messages
- **Done:** Prefer `{ error: { code, message } }` in `formatErrorMessage`; expose `ApiError.code` / `extractErrorCode`.
- **Files:** `types/api.ts`, `services/api.ts`, `services/api.test.ts`
- **Deferred:** None.

### FE-002 — Bootstrap treats public GET as JWT proof
- **Done:** Session proof via authenticated `GET /auth/me` (`getCurrentUser`). 401/403 clears local session.
- **Files:** `services/userBootstrap.ts`, `userBootstrap.test.ts`
- **BE sync:** Requires Agent F **BE-016** `/auth/me` (or equivalent). Dual-path not retained.

### FE-003 — No 401/403 handling
- **Done:** Central clear in `apiRequest` → `notifyAuthFailure` (latched) → `authStore.session = 'expired'`. Auth login/register/claim exempt. WatchlistRoot recovers on 401/403.
- **Files:** `services/api.ts`, `services/authSession.ts`, `stores/authStore.ts`, `WatchlistRoot.tsx`
- **Deferred:** Refresh-token flow (no BE contract).

### FE-004 — Hardcoded silent register/login
- **Done:** Silent `dev@local` gated by `allowDevAuth()` (`import.meta.env.DEV` or `VITE_ALLOW_DEV_AUTH`). Production path: `AuthGate` + `AuthModal` (login/register). Claim only as DEV fallback after login fails. Prefer login over claim on `EMAIL_EXISTS`.
- **Files:** `constants/auth.ts`, `userBootstrap.ts`, `components/Auth/AuthGate.tsx`, `AuthModal.tsx`, `AppShell.tsx`
- **BE sync:** Ship with **BE-002** claim removal / register+login only.

### FE-005 — Live candle WS unused
- **Done:** `LiveWsClient` + `useLiveCandles` (active pane only). Gated by `VITE_LIVE_WS`. Upserts via `ChunkManager.upsertLiveBar`. Auth `?token=`.
- **Files:** `services/liveWsClient.ts`, `hooks/useLiveCandles.ts`, `chunkManager.ts`, `useChunkManager.ts`, `ChartContainer.tsx`
- **Deferred:** Enable by default until **BE-019** + **BE-009** land; incomplete bars ignored when flagged.

### FE-006 — Screener/AI unused
- **Done (recommended B):** Client modules only — `scanApi.ts`, `aiApi.ts` (Bearer via `apiRequest`). No routes/UI yet.
- **Deferred:** Scan page + AI panels after BE-001/004/020/023.

### FE-007 — Backtest equity/overlays ignored
- **Done:** `normalizeBacktestRun` keeps `equity` / `signals` / `trades`. Equity sparkline on BacktestPage. Chart-data query supports `includeSignals` / `includeTrades` / `runId`. No client `user_id` on POST (already omitted).
- **Files:** `types/backtest.ts`, `backtestApi.ts`, `chartDataAdapter.ts`, `BacktestPage.tsx`, `EquitySparkline.tsx`
- **Deferred:** Full lightweight-charts markers on chart page when a run is selected (query flags ready).

### FE-008 — Leaving chart kills replay WS
- **Done:** `ReplayRoot` always mounted under AppShell (not pathname-gated). Resume reconnects when same session lacks OPEN socket without racing create.
- **Files:** `ReplayRoot.tsx`, `useReplaySession.ts`
- **BE sync:** Send `?token=` on WS (**BE-006**).

### FE-009 — Replay commands dropped when not OPEN
- **Done:** Outbound queue with coalesce (play/pause, seek, speed); flush on open; `pendingPlay` → phase `playing` after flush.
- **Files:** `replayWsClient.ts`, `useReplayWs.ts`, `replayWsClient.test.ts`

### FE-010 — Chunk prefetch key mismatch
- **Done:** Prefetch guards with `hasCoverage(priorStart, priorEnd)`; store still keyed by `data.start`.
- **Files:** `chunkManager.ts`, `useChunkManager.ts`, `chartDataWindow.test.ts`

### FE-011 — Empty windows / latest fallback
- **Done:** Defensive `isRangedFallbackResponse` (empty / `filledFromLatest` / no overlap) → skip `addChunk`, set `reachedEarliest`.
- **Files:** `utils/chartDataWindow.ts`, `useChunkManager.ts`, `types/chartData.ts`
- **BE sync:** Prefer empty + flag from chart-data (**BE-008** empty-window contract).

### FE-012 — Legend shows active-pane symbol/TF
- **Done:** `ChartLegend` accepts pane `symbol` / `timeframe` props from `ChartContainer`.
- **Files:** `ChartLegend.tsx`, `ChartContainer.tsx`

### FE-013 — Visible range sync across different symbols
- **Done:** `useMultiChartSync` skips range apply when symbols differ and `sync.symbol` is false. Sync panel copy updated.
- **Files:** `useMultiChartSync.ts`, `SyncConfigPanel.tsx`

### FE-014 — Indicators global, not per pane
- **Done:** `indicatorStore.byPane` + `editingPaneId`; ChartContainer reads `byPane[paneId]`; workspace active pane drives editing context.
- **Files:** `indicatorStore.ts`, `ChartContainer.tsx`, `WorkspaceRoot.tsx`

### FE-015 — Drawing interaction uses chartStore
- **Done:** `useDrawingInteraction` takes pane `symbolId` / `timeframe` from ChartContainer.
- **Files:** `useDrawingInteraction.ts`, `ChartContainer.tsx`

### FE-016 — Timeframe catalog incomplete
- **Done (recommended B):** Added `3m`, `2h`, `1w` to `TIMEFRAME_OPTIONS` + BacktestPage. **`1M` omitted** until BE-010.
- **Files:** `constants/chart.ts`, `BacktestPage.tsx`
- **Deferred:** Fetch `/meta/timeframes` (Solution A).

### FE-017 — Watchlist rename/delete unused
- **Done:** `getWatchlist` / `patchWatchlist` / `deleteWatchlist` API helpers; panel Rename / Delete / Set default.
- **Files:** `watchlistApi.ts`, `WatchlistRoot.tsx`, `WatchlistPanel.tsx`
- **BE sync:** Default toggle safest after **BE-013** + **BE-014**.

### FE-018 — Indicators not persisted
- **Done:** IDB `indicatorCache` (schema `global` | `byPane`); debounce-persist from store; hydrate in WorkspaceRoot.
- **Files:** `services/indicatorCache.ts`, `indicatorStore.ts`, `WorkspaceRoot.tsx`

---

## Cross-cutting files

| Area | Files |
|---|---|
| Auth UX | `AuthGate`, `AuthModal`, `authStore`, `authSession` |
| App shell | `AppShell.tsx` wraps `AuthGate` |

---

## Remaining gaps / coordination

1. **Hard release couples:** FE-002 ↔ BE-016 (`/auth/me`); FE-004 ↔ BE-002 (no claim); FE-011 ↔ BE empty-window; replay WS auth ↔ BE-006.
2. **FE-005** remains off until `VITE_LIVE_WS=true` and BE-009/019 ready.
3. **FE-006** clients only — no Scan/AI routes.
4. **FE-007** chart markers UI not fully drawn on chart canvas (query params + run equity UI shipped).
5. **FE-016** meta fetch and `1M` still deferred.
6. No JWT refresh (documented in FE-003).

---

## Env flags

| Flag | Purpose |
|---|---|
| `VITE_ALLOW_DEV_AUTH` | Force on/off silent local auth (`true`/`false`); default follows `DEV` |
| `VITE_LIVE_WS` | Enable `/ws/live` client |
| `VITE_LIVE_WS_URL` | Optional absolute live WS URL |
| `VITE_API_BASE` | API prefix (default `/api/v1`) |
