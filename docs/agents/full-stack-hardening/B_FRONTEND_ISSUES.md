# Agent B — Frontend Issues (incl. FE↔BE mismatches)

## Frontend Issues (incl. FE↔BE mismatches)

### FE-001
- **Title:** API client drops backend error messages
- **Area:** `frontend/src/services/api.ts`, `frontend/src/types/api.ts`
- **Description:** Backend `ApiError` responses use `{ "error": { "code", "message" } }` (`backend/api/schemas/common.py`, `backend/api/main.py`). FE `formatErrorMessage` only reads top-level `detail` / `message`, so most business errors surface as raw `statusText` (`Unauthorized`, `Unprocessable Entity`). `ApiErrorBody` type also omits the real envelope.
- **Impact:** Watchlist/auth/backtest/replay failures show useless messages; harder to debug and recover.
- **Category:** api-mismatch

### FE-002
- **Title:** Bootstrap treats public `GET /users/{id}` as proof of valid JWT
- **Area:** `frontend/src/services/userBootstrap.ts` ↔ `backend/api/routers/users.py`
- **Description:** With stored `user_id` + token, `ensureUserId` only calls `getUser(stored)`. BE `GET /users/{user_id}` is explicitly public (no JWT). Watchlists require Bearer auth (`backend/api/routers/watchlists.py` + `get_current_user`).
- **Impact:** Expired/invalid tokens still “bootstrap successfully”; subsequent watchlist calls fail with 401 and leave the UI in a stale/error state.
- **Category:** auth

### FE-003
- **Title:** No 401/403 handling or token refresh anywhere
- **Area:** `frontend/src/services/api.ts`, `WatchlistRoot.tsx`, `userBootstrap.ts`
- **Description:** `apiRequest` never clears tokens or re-auths on 401. BE JWTs expire (`jwt_expire_minutes`, default 7d). Watchlist recovery only special-cases `404 USER_NOT_FOUND`, not `UNAUTHORIZED` / `INVALID_TOKEN`.
- **Impact:** After expiry, watchlist mutations/loads break until manual localStorage wipe; no silent reclaim/login path.
- **Category:** auth

### FE-004
- **Title:** Hardcoded silent register/login as the only auth UX
- **Area:** `frontend/src/constants/auth.ts`, `frontend/src/constants/watchlist.ts`, `userBootstrap.ts`
- **Description:** FE auto-registers/claims/logs in as `dev@local` / `dev-local-password` with no login UI. Matches pipeline note that Phase 11 FE auth UI is incomplete, but this is production-risk behavior if pointed at a shared API.
- **Impact:** Shared backend gets a known shared account; no real user auth; credentials in source.
- **Category:** auth

### FE-005
- **Title:** Live candle WS exists on BE but FE never connects
- **Area:** FE chart loaders ↔ `backend/api/ws/live.py` (`/ws/live`)
- **Description:** BE ships DB-tail live updates (`subscribe` / `candle`). FE chart path is only REST `chart-data` + chunk prefetch (`useChunkManager.ts`); no `/ws/live` client.
- **Impact:** Charts stay frozen at last REST fetch until reload/scroll reload; “live” market view is stale.
- **Category:** api-mismatch

### FE-006
- **Title:** Screener/AI HTTP APIs unused by FE
- **Area:** App routes (`App.tsx`) ↔ `backend/api/routers/scan.py`, `backend/api/routers/ai.py`
- **Description:** BE exposes `POST /api/v1/scan` and `/ai/translate|clarify|explain`. FE only routes `/` and `/backtest`; no clients/types for scan or AI.
- **Impact:** Shipped backend features are unreachable from the UI.
- **Category:** api-mismatch

### FE-007
- **Title:** Backtest response equity/overlays ignored; chart overlays never wired
- **Area:** `frontend/src/services/backtestApi.ts`, `types/backtest.ts`, `chartDataAdapter.ts` ↔ `backend/api/schemas/backtest.py`, `chart_data.py`
- **Description:** BE `BacktestRunResponse` includes `equity`, `signals`, `trades`. FE `normalizeBacktestRun` drops them. BE `GET /chart-data` supports `includeSignals` / `includeTrades` / `runId`; FE never sends them. Backtest page text admits chart overlays are deferred.
- **Impact:** No equity curve UI; no trade/signal markers on chart even though BE supports them.
- **Category:** api-mismatch

### FE-008
- **Title:** Leaving chart route kills replay WS without reconnect
- **Area:** `frontend/src/components/Replay/ReplayRoot.tsx`, `hooks/useReplaySession.ts`, `hooks/useReplayWs.ts`
- **Description:** `ReplayRoot` only mounts hooks on `pathname === '/'`. Navigating to `/backtest` unmounts hooks → WS closed. Store/`?replaySession=` still hold the session. On return, resume logic short-circuits when `existing === sessionFromUrl && phase !== 'inactive'`, so it never reconnects.
- **Impact:** Replay UI looks active but Play/Step/Seek silently no-op (`ReplayWsClient.send` requires OPEN socket).
- **Category:** bug

### FE-009
- **Title:** Replay commands silently dropped when socket not open
- **Area:** `frontend/src/services/replayWsClient.ts`, `hooks/useReplaySession.ts`
- **Description:** `send()` returns without queue/retry if not `OPEN`. `play()` still sets local `phase: 'playing'` then sends `play`. Same for step/seek/speed during connect/reconnect gaps.
- **Impact:** Client thinks it is playing while server never advances; empty queue + no refill.
- **Category:** reliability

### FE-010
- **Title:** Chunk prefetch key mismatch (`priorStart` vs `data.start`)
- **Area:** `frontend/src/hooks/useChunkManager.ts`, `services/chunkManager.ts`
- **Description:** Prefetch guards with `hasChunk(priorStart)` but stores via `addChunk(data.start, …)`. Keys often differ (BE returns actual first-bar time as `start`).
- **Impact:** Repeated refetch of the same historical window on scroll-left; wasted API load; possible thrash near gaps.
- **Category:** bug

### FE-011
- **Title:** Empty chart-data windows fall back to latest bars (FE assumes empty/historical)
- **Area:** `useChunkManager.ts` ↔ `backend/api/services/chart_data_service.py` (+ `candle_service.get_latest_candles`)
- **Description:** If requested `[start,end]` has no bars, BE substitutes latest candles. FE scroll-back treats the response as the prior chunk.
- **Impact:** Gap/edge scroll-back can re-ingest “latest” data into the chunk map (redundant at best; confusing near holes / wrong anchors).
- **Category:** api-mismatch

### FE-012
- **Title:** Chart legend always shows active-pane symbol/timeframe
- **Area:** `frontend/src/components/Chart/ChartLegend.tsx` vs `ChartContainer` / `MultiChartLayout`
- **Description:** Candle series use `symbolOverride` / `timeframeOverride` per pane, but legend reads `useChartStore` only.
- **Impact:** In multi-chart (default `sync.symbol: false`), inactive panes show the wrong symbol/TF label over correct candles.
- **Category:** bug

### FE-013
- **Title:** Default sync couples visible ranges across unsynced symbols
- **Area:** `frontend/src/constants/workspace.ts`, `hooks/useMultiChartSync.ts`
- **Description:** Defaults: `visibleRange: true`, `symbol: false`. Logical ranges are published/applied across panes with different series lengths/symbols.
- **Impact:** Multi-symbol layouts jump/clip viewports incorrectly; sync feels broken out of the box.
- **Category:** state

### FE-014
- **Title:** Indicators are global, not per pane
- **Area:** `frontend/src/stores/indicatorStore.ts`, `ChartContainer.tsx`
- **Description:** One `indicatorStore` feeds every pane’s `useChunkManager` / overlays. Workspace panes only store symbol/TF.
- **Impact:** Cannot show RSI on one pane and clean price on another; every layout pane pays for the same indicator compute payload.
- **Category:** ux

### FE-015
- **Title:** Drawing create/hit-test keyed off chartStore, not pane props
- **Area:** `frontend/src/hooks/useDrawingInteraction.ts` vs `DrawingsLayer` / `useDrawings`
- **Description:** Layer filters by pane `symbolId`/`timeframe` correctly; interaction always tags/selects using `useChartStore` (active pane). Works only while active pane mirrors store; race on fast pane switches / tool still armed.
- **Impact:** Drawings can be saved under the wrong symbol/TF or hit-tested against the wrong set after pane switches.
- **Category:** state

### FE-016
- **Title:** FE timeframe catalog incomplete vs BE
- **Area:** `frontend/src/constants/chart.ts` ↔ `backend/api/services/timeframes.py` (+ unused `GET /meta/timeframes`)
- **Description:** FE offers `1m,5m,15m,30m,1h,4h,1d`. BE also supports `3m,2h,1w,1M`. FE never loads `/meta/timeframes`.
- **Impact:** Valid BE data ranges/timeframes unreachable from chart UI; backtest page list also incomplete vs chart.
- **Category:** api-mismatch

### FE-017
- **Title:** Watchlist FE never uses rename/delete/get-one endpoints
- **Area:** `frontend/src/services/watchlistApi.ts` ↔ `backend/api/routers/watchlists.py`
- **Description:** BE has `GET/PATCH/DELETE /users/{id}/watchlists/{wid}`. FE only list/create/replace-symbols.
- **Impact:** No rename/delete/default toggle in UI; orphan lists accumulate; incomplete CRUD vs BE.
- **Category:** api-mismatch

### FE-018
- **Title:** Active indicators not persisted across reload
- **Area:** `indicatorStore.ts` vs `workspaceStorage.ts` / `drawingCache.ts` / `watchlistCache.ts`
- **Description:** Workspace, drawings, watchlists persist (IDB). Indicators live only in memory.
- **Impact:** Reload wipes overlays/subpanes; mid-replay indicator set also lost on refresh (session URL alone is not enough).
- **Category:** ux

---

## Scope covered

- **FE structure:** stores (chart/workspace/replay/watchlist/drawing/indicator/layout/sync), services (`api`, auth bootstrap, chart-data, replay REST/WS, watchlist, backtest, caches), hooks (chunk manager, replay session/WS/tick, drawings, multi-chart sync), pages (`/`, `/backtest`), multi-chart layout.
- **BE cross-check:** routers under `/api/v1` (auth, users, watchlists, symbols, chart-data, indicators, candles, replay, backtest, scan, ai, meta), WS (`/ws/replay/{id}`, `/ws/live`), schemas/error envelope, JWT deps.
- **Not claimed as FE bugs:** style-only nits; intentional client-only drawings (no BE drawings API); structure/SMC/patterns (library modules without FE chart API surface).