# Agent E — Frontend Solutions Design

**Sources:** `B_FRONTEND_ISSUES.md`, `C_SEVERITY_DEPENDENCY.md`  
**Consumers:** Agent H (frontend implementer), Agent F (backend contract owners)  
**Scope:** Design only — no code in this artifact.

**Stack assumptions:** React + TypeScript + Zustand + Vite; existing services (`api.ts`, bootstrap, chart-data, replay WS), hooks (`useChunkManager`, replay/drawing/sync), and IDB caches (`workspaceStorage`, `drawingCache`, `watchlistCache`).

**Wave map (from Agent C):**
| Wave | FE issues |
|---|---|
| **1** Auth path | FE-001 → FE-002 → FE-003 → FE-004 |
| **2** Replay + chart correctness | FE-009 → FE-008; FE-011 → FE-010 |
| **3** Multi-pane + product wiring | FE-015, FE-013, FE-012, FE-007, FE-005 |
| **4** Deferrable surface | FE-016, FE-017, FE-018 → FE-014, FE-006 |

---

## Remediation summary (recommended track)

1. **Wave 1:** Error envelope → JWT proof bootstrap → 401 clear/re-auth → real login UI (gated on BE-002/003/016).
2. **Wave 2:** Replay command queue → route-stable reconnect; empty-window contract + chunk key unify.
3. **Wave 3:** Pane-aware drawings/legend/sync; then backtest overlays; then live WS after BE-009/019.
4. **Wave 4:** Meta timeframes (after BE-010 for `1M`); watchlist CRUD; persist indicators then per-pane; screener/AI last.

---

### FE-001 — API client drops backend error messages
- Severity / Wave: **High / Wave 1** (rank 25; blocks FE-002/003/004/017)
- Solution A: Extend `ApiErrorBody` + `formatErrorMessage` to read `{ error: { code, message } }` first, keep FastAPI `detail` / top-level `message` fallbacks; expose `code` on `ApiError`.
- Solution B: Add a dedicated `parseApiError(body)` util used by `apiRequest` and bootstrap; map known codes to user-facing copy in a small dictionary.
- Solution C: Rely on React Query / toast layers to stringify `error.body` ad hoc (no shared parser).
- **Recommended:** A (minimal, unblocks auth branching immediately; B’s copy map can follow later)
- Implementation sketch:
  - Update `ApiErrorBody` to include optional nested `error: { code?: string; message?: string }`.
  - Prefer nested `message` in `formatErrorMessage`; attach `code` (and optionally keep raw body) on `ApiError`.
  - Align `getErrorCode` in bootstrap to use `ApiError.code` once present.
  - Unit-test envelope, FastAPI `detail` string/array, and text fallbacks.
- Files: `frontend/src/types/api.ts`, `frontend/src/services/api.ts`, `frontend/src/services/userBootstrap.ts` (thin), existing `api` / bootstrap tests
- Risk/tradeoffs: Low; wrong priority order could hide FastAPI validation messages if nested shape is empty — keep ordered fallbacks.
- BE coordination: None required. Envelope already defined in `backend/api/schemas/common.py` / `main.py`. Ship FE independently in Wave 1.

---

### FE-002 — Bootstrap treats public `GET /users/{id}` as proof of valid JWT
- Severity / Wave: **High / Wave 1** (rank 26; depends FE-001 + BE-016; blocks FE-003/004)
- Solution A: Replace “stored + getUser” success with an authenticated probe (`GET /auth/me` or authenticated watchlist list / future `/users/me`). On 401, clear session and fall through to obtain token.
- Solution B: Keep `getUser` for profile display only; separately validate JWT by calling any already-auth’d endpoint (e.g. `listWatchlists`) before marking bootstrap OK.
- Solution C: Decode JWT client-side (`exp` check) and skip network proof.
- **Recommended:** A (single contract with BE-016 lockdown; avoids treating public GET as session proof)
- Implementation sketch:
  - Agree with Agent F: prefer `GET /auth/me` (or make `GET /users/{id}` require Bearer and return 401 on bad token).
  - In `ensureUserIdOnce`, when `stored && token`, call the authenticated probe; on 401/403 clear token + user + watchlist cache, then register/login path.
  - Stop treating bare 200 from public GET as “session valid”.
  - Update `userBootstrap.test.ts` for expired-token → reclaim cases.
- Files: `frontend/src/services/userBootstrap.ts`, `frontend/src/services/authToken.ts`, optional new `authApi.ts`, tests
- Risk/tradeoffs: Must ship in the same release as BE-016 or bootstrap breaks when public GET is removed; Solution C misses revoked tokens.
- BE coordination: **Hard sync with BE-016** (and trustworthy secret BE-003). Do not land FE-002 against old public-GET-only world without a temporary dual path. Prefer new `/me` (or auth-required GET) agreed before H starts.

---

### FE-003 — No 401/403 handling or token refresh anywhere
- Severity / Wave: **High / Wave 1** (rank 27; depends FE-001/002; blocks FE-004)
- Solution A: Centralize in `apiRequest`: on 401/403 clear token + user id, emit a small auth-event (or Zustand auth flag), and let callers / WatchlistRoot re-bootstrap or show login.
- Solution B: Per-feature catchers only (WatchlistRoot, backtest, replay) that call `clearLocalUserId` and retry `ensureUserId`.
- Solution C: Full silent refresh-token flow (needs BE refresh endpoint — not present today).
- **Recommended:** A (one choke point; fits current Bearer-only JWT; pairs with FE-004 login UX)
- Implementation sketch:
  - After FE-001, branch on status + `error.code` (`UNAUTHORIZED`, `INVALID_TOKEN`, etc.).
  - Clear storage once (guard against multi-request stampede).
  - Optionally return a typed `AuthRequiredError` or set `useAuthStore.session = 'expired'`.
  - WatchlistRoot: treat auth-expired like `USER_NOT_FOUND` recovery, but after FE-004 route to login instead of silent `dev@local`.
  - No refresh until BE adds refresh tokens — document that explicitly.
- Files: `frontend/src/services/api.ts`, `frontend/src/services/userBootstrap.ts`, `frontend/src/components/Watchlist/WatchlistRoot.tsx`, optional `stores/authStore.ts`
- Risk/tradeoffs: Aggressive clear can interrupt in-flight UI; stampede of parallel 401s needs a latch. Solution B will miss new callers.
- BE coordination: Align error codes with BE auth deps after BE-003/016. Replay ownership (BE-006) will also emit 401 on WS/REST — same clear path should apply. No refresh contract yet; do not invent FE-only refresh.

---

### FE-004 — Hardcoded silent register/login as the only auth UX
- Severity / Wave: **High / Wave 1** (rank 28; depends FE-001..003 + BE-002/003/012/015)
- Solution A: Gate silent `dev@local` behind `import.meta.env.DEV` (or `VITE_ALLOW_DEV_AUTH`); production builds show Login/Register modal (email/password) using existing `/auth/register` + `/auth/login`; remove claim from happy path once BE-002 kills takeover.
- Solution B: Always require explicit login UI; keep a “Continue as local demo” button only when API is localhost.
- Solution C: OAuth / magic-link only (larger BE scope).
- **Recommended:** A (pragmatic for Vite local DX; removes shared-account risk in non-dev builds once BE identity is fixed)
- Implementation sketch:
  - Extract `obtainDevToken` behind env flag; production `ensureUserId` only restores validated session or returns “needs auth”.
  - Add minimal Login/Register form (AppShell or modal) wired to `registerUser` / `loginUser`.
  - Remove hardcoded password from production bundles (tree-shake constants or move to `.env.local` for dev only).
  - Handle uniform auth errors after BE-024 (no existence oracle UX).
  - Assume default watchlist exists (BE-012); surface clear error if missing.
- Files: `frontend/src/constants/auth.ts`, `frontend/src/constants/watchlist.ts`, `userBootstrap.ts`, new `components/Auth/*`, `AppShell.tsx` / `WatchlistRoot.tsx`, tests
- Risk/tradeoffs: Breaking change for anyone relying on silent shared account; must coordinate release with BE claim lockdown.
- BE coordination: **Ship after / with BE-002, BE-003, BE-012, BE-015.** Stop using `/auth/claim` for normal UX once passwordless create is gone. Match register/login error shapes from BE-024. Email normalization expectations from BE-015.

---

### FE-005 — Live candle WS exists on BE but FE never connects
- Severity / Wave: **Medium / Wave 3** (rank 37; depends BE-009, BE-019)
- Solution A: Add `LiveWsClient` mirroring `ReplayWsClient`; subscribe active pane symbol(s)/TF; merge `candle` events into chunk manager / series via a `useLiveCandles` hook (replace or append last bar).
- Solution B: Poll REST `chart-data` / latest candles on an interval as a temporary “live” mode without WS.
- Solution C: Only live-update the active pane; other panes stay REST-only until needed.
- **Recommended:** A + C hybrid (real WS, scoped to visible/active subscriptions to limit fan-out) — **after** BE-019/009
- Implementation sketch:
  - Wait for BE pooled DB access + incomplete-bucket policy.
  - Implement client + hook; auth headers/query if BE-004/006-style auth lands on live WS.
  - On event: upsert bar by time into assembled series; ignore incomplete higher-TF if BE marks them.
  - Reconnect with backoff; resubscribe on symbol/TF change.
  - Feature-flag until BE ready (`VITE_LIVE_WS`).
- Files: new `services/liveWsClient.ts`, `hooks/useLiveCandles.ts`, `useChunkManager.ts` / `ChartContainer.tsx`, types
- Risk/tradeoffs: Early adoption amplifies BE-019 connection churn and BE-009 wrong bars; multi-pane N subscriptions need care.
- BE coordination: **Do not start until BE-019 + BE-009.** Confirm subscribe payload (`symbols`, timeframe), auth once BE-004 gates live, and how incomplete buckets are signaled.

---

### FE-006 — Screener/AI HTTP APIs unused by FE
- Severity / Wave: **Low / Wave 4** (rank 42; depends BE-001/004/020/023 + FE-001)
- Solution A: Thin Phase-1 UI: `/scan` page posting to `POST /api/v1/scan` + retrieve when BE-023 exists; separate light “Explain” / “Translate” panels on backtest/chart calling `/ai/*` with auth.
- Solution B: Ship API clients + types only (no routes) so Agent H can wire UI later; document in pipeline.
- Solution C: Full productized screener + multi-turn AI clarify workspace (large scope).
- **Recommended:** B now, then A after BE wave (clients-first avoids dead UI against broken persist/sessions)
- Implementation sketch:
  - Wave 4 start: `scanApi.ts` / `aiApi.ts` + types; parse errors via FE-001.
  - After BE-001/023: Scan page with run + poll/retrieve; show `persisted` honestly.
  - After BE-004/020: AI panels require token; bind clarify `session_id` to user; handle multi-worker-safe retrieve.
  - Add routes in `App.tsx` only when UX is ready.
- Files: new services/types/pages, `App.tsx`, nav in `AppShell`
- Risk/tradeoffs: Building full UI before BE-001/023 wastes work and trains users on false `persisted`.
- BE coordination: Gate on BE-001, BE-004, BE-020, BE-023. FE must send Bearer once endpoints require auth. Prefer retrieve-by-id contract before rich history UI.

---

### FE-007 — Backtest response equity/overlays ignored; chart overlays never wired
- Severity / Wave: **Medium / Wave 3** (rank 36; depends BE-007, BE-005, BE-009)
- Solution A: Extend `normalizeBacktestRun` to keep `equity`, `signals`, `trades`; render equity chart on BacktestPage; pass `includeSignals`/`includeTrades`/`runId` into chart-data when viewing a run; draw markers via lightweight-charts.
- Solution B: Only show tabular trades/metrics on BacktestPage; skip chart overlays until a dedicated “analyze run on chart” flow exists.
- Solution C: Fetch overlays solely via chart-data flags and discard series from run response (single source).
- **Recommended:** A (BE already returns both; richest UX once window/attribution/closed-bar fixes land)
- Implementation sketch:
  - Types + normalizer for equity/signals/trades.
  - Stop sending client `user_id` once BE-005 binds JWT (omit field).
  - Equity sparkline/chart on results panel.
  - Chart path: when `runId` selected, `fetchChartData({ includeSignals, includeTrades, runId })` and map to markers.
  - Guard near-now overlays after BE-009.
- Files: `types/backtest.ts`, `backtestApi.ts`, `chartDataAdapter.ts` / chart-data fetch, `BacktestPage.tsx`, chart overlay components, tests
- Risk/tradeoffs: Showing overlays before BE-007 makes wrong windows look authoritative; large marker sets can hurt perf — downsample if needed.
- BE coordination: **After BE-007 (timestamptz windows), BE-005 (drop spoofable user_id), BE-009 (closed bars).** Confirm chart-data query aliases (`includeSignals`, `includeTrades`, `runId`).

---

### FE-008 — Leaving chart route kills replay WS without reconnect
- Severity / Wave: **High / Wave 2** (rank 30; depends FE-009 + BE-006/018)
- Solution A: Lift `ReplayRoot` hooks to `AppShell` (or always-mounted provider) so `/backtest` navigation does not unmount WS; keep UI chrome route-aware.
- Solution B: Keep mount-on-`/`, but fix resume: on remount if `sessionFromUrl` matches and socket missing, force reconnect instead of short-circuit; rely on FE-009 queue.
- Solution C: Persist WS in a module singleton outside React tree.
- **Recommended:** A (prevents the bug class; B is acceptable hotfix if lift is too large)
- Implementation sketch:
  - Prefer mounting replay session/WS under `AppShell` while chart-only controls stay on `/`.
  - If A is deferred: change `useReplaySession` resume guard to reconnect when `getWsClient()` not OPEN.
  - On reconnect, resync phase from server events; flush FE-009 queue.
  - Send Bearer on WS when BE-006 requires it.
- Files: `ReplayRoot.tsx`, `AppShell.tsx`, `hooks/useReplaySession.ts`, `useReplayWs.ts`, tests
- Risk/tradeoffs: Always-on WS uses resources off chart route; singleton (C) harder to test/StrictMode. B alone is easier but easier to regress.
- BE coordination: Pair with BE-006 (auth on create/WS) and BE-018 (stable handler). Client must handle 401/not_found without assuming anonymous UUID forever.

---

### FE-009 — Replay commands silently dropped when socket not open
- Severity / Wave: **High / Wave 2** (rank 29; blocks FE-008; align BE-018)
- Solution A: Outbound command queue in `ReplayWsClient.send`: enqueue if not OPEN; flush on `onopen`; do not set local `playing` until server ack / or set `connecting`/`buffering` phase until flush succeeds.
- Solution B: Disable Play/Step/Seek in UI while connection ≠ open; show reconnecting state (no queue).
- Solution C: Optimistic phase + periodic resend of last desired state (play/pause/speed) on interval.
- **Recommended:** A (preserves intent across reconnect; B alone feels broken during brief gaps)
- Implementation sketch:
  - Queue `play|pause|step|seek|speed` with coalescing rules (e.g. latest speed wins; seek replaces prior seek).
  - `play()` sets phase to `connecting`/`pending_play` until open+flushed or server confirms.
  - Cap queue size; drop/error if socket dies permanently.
  - Unit-test gap: call play before open → server receives after open.
- Files: `services/replayWsClient.ts`, `hooks/useReplaySession.ts`, `stores/replayStore.ts` (phase), tests
- Risk/tradeoffs: Stale queued seeks after user navigates away — clear queue on session stop. Optimistic UI (current) is the bug; A fixes correctness with slight UX delay.
- BE coordination: Align with BE-018 bad-frame resilience. When BE-006 adds auth failures, map close codes to clear queue + auth recovery (FE-003).

---

### FE-010 — Chunk prefetch key mismatch (`priorStart` vs `data.start`)
- Severity / Wave: **Medium / Wave 2** (rank 32; depends BE-008; after FE-011)
- Solution A: Key chunks by returned `data.start` (and optionally `data.end`); before fetch, check overlap / existing coverage via candle time range rather than requested `priorStart`.
- Solution B: Force BE to echo request `start` as map key (contract change); FE keeps request-key guards.
- Solution C: Always use `next_from` / cursor from prior response for pagination instead of computed `priorStart`.
- **Recommended:** A (FE-local, matches real data; C as enhancement once BE-008 keyset is stable)
- Implementation sketch:
  - Change `hasChunk` usage: `hasCoverage(priorStart, priorEnd)` or normalize key to first bar time after fetch and record requested→actual alias.
  - After FE-011, reject latest-fallback payloads so wrong keys never enter the map.
  - Add regression test: request start ≠ response start → no second fetch.
- Files: `services/chunkManager.ts`, `hooks/useChunkManager.ts`, tests
- Risk/tradeoffs: Overlap checks are slightly more complex than equality; B couples FE to a brittle BE echo.
- BE coordination: Prefer after BE-008 stable `start`/`next_from`. Combine with empty-window policy from FE-011. Optional later move to C when keyset cursors are documented.

---

### FE-011 — Empty chart-data windows fall back to latest bars (FE assumes empty/historical)
- Severity / Wave: **High / Wave 2** (rank 31; blocks FE-010; coordinate BE empty-window + BE-008)
- Solution A: FE detects “fallback” (e.g. response window not intersecting request, or explicit `filledFromLatest` / empty flag) and does **not** `addChunk` as prior history; mark edge exhausted.
- Solution B: Rely solely on BE change: return empty candles + no fallback; FE treats empty as end-of-history.
- Solution C: FE always verifies `data.candles[0].time` within requested `[start,end]` before ingesting.
- **Recommended:** A+B together — **B as source of truth, A/C as defensive client** (ship FE guard even before BE lands)
- Implementation sketch:
  - Agree contract: prefer empty array + `truncated: true` / no latest substitution for ranged requests.
  - FE ingest guard: if no overlap with `[priorStart, priorEnd]`, skip add + set `reachedEarliest`.
  - Keep latest-bars behavior only for explicit “load latest” initial fetch (no start/end).
  - Tests for gap scroll-back and empty hole.
- Files: `useChunkManager.ts`, chart-data types/adapter, tests; BE `chart_data_service.py` (F)
- Risk/tradeoffs: FE-only (A/C) can false-negative if clocks/gaps weird; BE-only (B) leaves old clients vulnerable until upgrade — ship both.
- BE coordination: **Explicit empty-window contract with Agent F** (related BE-008). Same release note: ranged GET must not silently substitute latest.

---

### FE-012 — Chart legend always shows active-pane symbol/timeframe
- Severity / Wave: **Low / Wave 3** (rank 35; no deps)
- Solution A: Pass `symbol` / `timeframe` props into `ChartLegend` from `ChartContainer` (resolved overrides), stop reading active pane from `useChartStore` for labels.
- Solution B: Legend reads pane id from context and looks up workspace pane config.
- Solution C: Hide legend symbol/TF text on inactive panes.
- **Recommended:** A (matches how candles already resolve overrides; smallest fix)
- Implementation sketch:
  - Thread props from `ChartContainer` → `ChartLegend`.
  - Keep store only for panes without overrides.
  - Snapshot test / multi-pane manual check with `sync.symbol: false`.
- Files: `ChartLegend.tsx`, `ChartContainer.tsx`, possibly `MultiChartLayout.tsx`
- Risk/tradeoffs: Negligible; B is more indirection for same result.
- BE coordination: None.

---

### FE-013 — Default sync couples visible ranges across unsynced symbols
- Severity / Wave: **Medium / Wave 3** (rank 34; no deps)
- Solution A: Change default `visibleRange` to `false` when `symbol` sync is false; or default both range + symbol off for multi-symbol layouts (`constants/workspace.ts`).
- Solution B: Keep defaults but in `useMultiChartSync` only apply range sync across panes that share symbol (and optionally TF).
- Solution C: Sync time (unix) range instead of logical bar indices across symbols.
- **Recommended:** B (preserves TV-like range sync for same-symbol layouts; fixes default multi-symbol pain without killing the feature)
- Implementation sketch:
  - When applying `visibleRange` events, skip targets where `pane.symbol !== source.symbol` (unless `sync.symbol`).
  - Optionally update default copy in SyncConfigPanel to explain coupling.
  - Consider A as additional safe default if product prefers opt-in range sync.
  - Tests in `syncStore` / `useMultiChartSync`.
- Files: `hooks/useMultiChartSync.ts`, `constants/workspace.ts`, `SyncConfigPanel.tsx`, tests
- Risk/tradeoffs: C is more correct cross-symbol but heavier; A alone may surprise users who want same-symbol range sync on by default.
- BE coordination: None.

---

### FE-014 — Indicators are global, not per pane
- Severity / Wave: **Low / Wave 4** (rank 41; depends FE-018 persistence model)
- Solution A: Key `indicatorStore` active sets by `paneId` (workspace pane); IndicatorPanel / `useChunkManager` read pane-local active list.
- Solution B: Keep global indicators but allow per-pane mute/override map in workspace pane config.
- Solution C: Separate Zustand stores per mounted `ChartContainer` via provider.
- **Recommended:** A (clean model; do **after** FE-018 so persistence shape matches pane scope)
- Implementation sketch:
  - Extend workspace pane type with `indicators?: …` or store `Record<paneId, ActiveIndicator[]>`.
  - Migrate FE-018 persisted blob from global → per-pane (default pane gets current global set).
  - ChartContainer passes `paneId` into indicator hooks/fetch specs.
  - UI: panel edits active pane only.
- Files: `indicatorStore.ts`, `workspace` types/store, `ChartContainer.tsx`, `IndicatorPanel.tsx`, `useChunkManager.ts`, persistence (FE-018)
- Risk/tradeoffs: More API payload if every pane requests different indicators; migration from global persistence needed.
- BE coordination: None for store shape; chart-data already accepts indicator specs per request.

---

### FE-015 — Drawing create/hit-test keyed off chartStore, not pane props
- Severity / Wave: **Medium / Wave 3** (rank 33; no deps)
- Solution A: Pass `symbolId` / `timeframe` into `useDrawingInteraction` from pane props (same source as `DrawingsLayer` / `useDrawings`).
- Solution B: On every pointer event, resolve symbol/TF from “pane under cursor” registry instead of props/store.
- Solution C: Disable drawing tools unless the pane is the active chartStore pane.
- **Recommended:** A (consistent with layer filtering; fixes race without disabling UX)
- Implementation sketch:
  - Thread overrides from `ChartContainer` into the interaction hook.
  - Create/select/hit-test only against that pane’s symbol/TF.
  - Add test: switch active pane with tool armed → drawing still tagged to interaction pane.
  - Optional: sync chartStore on pane focus separately from drawing identity.
- Files: `hooks/useDrawingInteraction.ts`, `DrawingsLayer.tsx`, `ChartContainer.tsx`, tests
- Risk/tradeoffs: C is a product limitation. B is more complex than needed for fixed panes.
- BE coordination: None (client-only drawings).

---

### FE-016 — FE timeframe catalog incomplete vs BE
- Severity / Wave: **Low / Wave 4** (rank 38; depends BE-010 before `1M`)
- Solution A: Fetch `GET /meta/timeframes` at app bootstrap; drive selectors from API; keep static list as offline fallback.
- Solution B: Statically extend `TIMEFRAME_OPTIONS` with `3m,2h,1w` now; add `1M` only after BE-010.
- Solution C: Hardcode full BE list including `1M` immediately.
- **Recommended:** B short-term, A as follow-up (fast unblock without waiting on meta UX; avoid `1M` until BE-010)
- Implementation sketch:
  - Patch `constants/chart.ts` (+ backtest TF list) with safe extras.
  - Feature-flag or omit `1M` until Agent F aligns month semantics.
  - Later: `metaApi.getTimeframes()` + React Query; validate against known set.
- Files: `constants/chart.ts`, backtest page constants, optional `services/metaApi.ts`, selectors
- Risk/tradeoffs: Static drift if BE adds TFs; A needs loading/error states. C spreads BE-010 bugs.
- BE coordination: **Do not expose `1M` until BE-010.** Meta endpoint already exists — wire when convenient.

---

### FE-017 — Watchlist FE never uses rename/delete/get-one endpoints
- Severity / Wave: **Low / Wave 4** (rank 39; depends FE-001, BE-013, BE-014)
- Solution A: Add `getWatchlist` / `patchWatchlist` / `deleteWatchlist` in `watchlistApi.ts`; UI: rename inline, delete with confirm, default toggle via PATCH `is_default`.
- Solution B: Delete-only + rename via recreate (delete+create) without PATCH — weaker.
- Solution C: Full watchlist management page separate from sidebar.
- **Recommended:** A (matches BE CRUD; sidebar actions are enough)
- Implementation sketch:
  - API helpers + types for PATCH body (`name`, `is_default`).
  - WatchlistPanel context menu / row actions; optimistic Zustand updates + cache sync.
  - Use FE-001 codes for ownership/validation errors.
  - Default toggle: only after BE-014 unique + BE-013 safe ordering — otherwise risk zero-default.
- Files: `watchlistApi.ts`, `types/watchlist.ts`, `watchlistStore.ts`, `WatchlistPanel.tsx` / row components, tests
- Risk/tradeoffs: Premature default toggle hits BE-013 footgun; delete needs confirm to avoid data loss.
- BE coordination: **After BE-013 + BE-014.** Confirm PATCH schema and default semantics. Auth via FE-001/003.

---

### FE-018 — Active indicators not persisted across reload
- Severity / Wave: **Low / Wave 4** (rank 40; blocks FE-014; prefer before FE-014)
- Solution A: Persist active indicators (+ appearance) in IDB alongside workspace (extend `workspaceStorage` or new `indicatorCache.ts`), rehydrate on bootstrap.
- Solution B: Persist in `localStorage` JSON keyed by workspace id (simpler, smaller quota).
- Solution C: Persist to BE user preferences API (does not exist).
- **Recommended:** A (consistent with drawings/watchlists IDB pattern; prepares per-pane migration for FE-014)
- Implementation sketch:
  - Serialize `ActiveIndicator[]` (and layout subpane heights if needed).
  - Save on store changes (debounce); load in workspace bootstrap.
  - Schema version field for FE-014 pane-keyed migration.
  - Replay: rehydrate before indicator sync hook runs.
- Files: `indicatorStore.ts`, `services/workspaceStorage.ts` or `indicatorCache.ts`, workspace bootstrap, tests
- Risk/tradeoffs: Stale catalog keys after indicator registry changes — drop unknown keys on load. localStorage (B) is fine for MVP but inconsistent with existing IDB.
- BE coordination: None. Prefer completing before FE-014 so persistence schema versions once.

---

## Cross-issue implementation notes for Agent H

| Order | Issue | Can parallelize with |
|---|---|---|
| 1 | FE-001 | BE Wave 1 (immediately) |
| 2–4 | FE-002 → FE-003 → FE-004 | BE-016 / BE-002 contract freeze |
| 5–6 | FE-009 → FE-008 | BE-006, BE-018 |
| 7–8 | FE-011 → FE-010 | BE-008 + empty-window policy |
| 9–11 | FE-015, FE-013, FE-012 | each other (FE-only) |
| 12–13 | FE-007, FE-005 | after listed BE deps |
| 14–18 | FE-016, FE-017, FE-018, FE-014, FE-006 | Wave 4; FE-018 before FE-014 |

**Do not start early:** FE-005, FE-006 (amplify unfinished BE debt).  
**Same-release pairs:** FE-002 ↔ BE-016; FE-004 ↔ BE-002/024; FE-011 ↔ chart empty-window; FE-008/009 ↔ BE-006 auth on replay WS.
