# Agent H (Loop 2) — Frontend Implementation

**Date:** 2026-08-11
**Repo:** `/Users/sohailmulla/projects/crypto-backtester`
**Inputs:** `LOOP2_B_FRONTEND_ISSUES.md`, `LOOP2_C_SEVERITY_DEPENDENCY.md`, `LOOP2_E_FRONTEND_SOLUTIONS.md`
**Scope:** Implement the **Recommended** solution for every `FE-L2-*` issue.

---

## Summary

| Status   | Count | IDs                                                                             |
|----------|------:|---------------------------------------------------------------------------------|
| Done     |    11 | FE-L2-001, -002, -003, -004, -005, -006, -007, -008, -009, -010, -011           |
| Partial  |     0 | —                                                                               |
| Blocked  |     0 | —                                                                               |

**Test totals:** `cd frontend && npm test -- --run` → **51 files, 205 tests, 205 passed** (baseline before H was 44 files / 175 tests; H adds 7 new files / 30 new tests and updates 4 existing files without regressions).

**G3-specific spot-check** (`useChunkManager.test.tsx`, `replayWsClient.test.ts`, `userBootstrap.test.ts`, `chartDataWindow.test.ts`, `api.test.ts`) → **5 files, 27 tests, all passing**.

**TypeScript check:** `npx tsc --noEmit` → clean.

---

## Cross-cutting artefacts introduced

Three new modules land as shared primitives that several issues consume together:

- `frontend/src/services/wsCloseCode.ts` — `WS_CLOSE_UNAUTHORIZED / _SUPERSEDED / _NOT_FOUND / _RATE_LIMITED` constants + `classifyWsCloseKind(code)`. Consumed by both `LiveWsClient` and `ReplayWsClient` (FE-L2-002 / -007).
- `frontend/src/services/wsTicketClient.ts` — `isWsTicketAuthEnabled()`, `getWsTicket()`, `getWsConnectUrl(baseUrl)`. Wraps `POST /api/v1/ws/tickets` and appends `?ticket=` (or falls back to legacy `?token=`) so both WS clients share the same auth path (FE-L2-003).
- `frontend/src/services/authToken.ts` — rewritten as an in-memory bearer store with a one-time legacy `localStorage['auth_token']` drain on module load (FE-L2-003).

Feature flag: `VITE_WS_TICKET`. Default is **on in production** (i.e. any build where `import.meta.env.DEV` is falsy) and **off in dev/test** unless explicitly set to `true`, so this FE lands cleanly ahead of / behind the BE endpoint.

---

## Per-issue results

### FE-L2-001 — Live WS `bar` vs `candle` field mismatch — **Done**

**Change:** `LiveWsClient.onmessage` now reads `row.bar` (not `row.candle`), drops the shorthand `c.t/c.o/...` fallbacks (BE always emits long-form), and no longer emits a phantom `incomplete` flag. `useLiveCandles` drops the corresponding `if (payload.incomplete) return` guard.

**Files:**
- `frontend/src/services/liveWsClient.ts` (rewrite)
- `frontend/src/hooks/useLiveCandles.ts` (rewrite)
- `frontend/src/services/liveWsClient.test.ts` **(new)**

**Tests added:** `reads row.bar and emits an OHLCVBar payload`, `ignores legacy row.candle payloads (contract truthing)`.

---

### FE-L2-002 — Live WS `onClose` discards close code — **Done**

**Change:** `LiveWsHandlers.onClose` now receives `{ code, reason, kind }` (same shape as `ReplayWsClient`, via the shared `classifyWsCloseKind` helper). `useLiveCandles` wires `kind === 'unauthorized'` → `notifyAuthFailure('UNAUTHORIZED')` + "Session expired" toast, and `kind === 'rate_limited'` → "Too many concurrent WebSocket connections" toast.

**Files:**
- `frontend/src/services/wsCloseCode.ts` **(new)**
- `frontend/src/services/liveWsClient.ts`
- `frontend/src/hooks/useLiveCandles.ts`
- `frontend/src/services/wsCloseCode.test.ts` **(new)**
- `frontend/src/services/liveWsClient.test.ts` **(new)**

**Tests added:** `classifyWsCloseKind` covers 4401/4402/4404/4429/1000/1001/other; `LiveWsClient` `onClose` test covers 4401, 4429, 1000.

---

### FE-L2-003 — JWT in localStorage + `?token=` WS query — **Done**

**Change:**
- `authToken.ts` rewritten as an in-memory bearer store; module init drains any legacy `localStorage['auth_token']` value into memory and removes the storage key so old sessions migrate cleanly across the release boundary.
- New `wsTicketClient.ts` exposes `getWsTicket()` (POSTs to `/api/v1/ws/tickets`) and `getWsConnectUrl(baseUrl)` — the single URL builder both WS clients now call. Ticket usage is env-flagged by `VITE_WS_TICKET` (default: `true` in prod, `false` in dev/test).
- `LiveWsClient.connect()` and `ReplayWsClient.connect()` are now `async` and await the ticket / URL builder before constructing the WebSocket. Callers (`useLiveCandles`, `useReplayWs`) have been updated to `void client.connect(...).catch(...)`.

**Files:**
- `frontend/src/services/authToken.ts` (rewrite)
- `frontend/src/services/wsTicketClient.ts` **(new)**
- `frontend/src/services/liveWsClient.ts`
- `frontend/src/services/replayWsClient.ts`
- `frontend/src/hooks/useLiveCandles.ts`
- `frontend/src/hooks/useReplayWs.ts`
- `frontend/src/services/authToken.test.ts` **(new)**
- `frontend/src/services/wsTicketClient.test.ts` **(new)**
- `frontend/src/services/api.test.ts` (updated — uses `setAuthToken` instead of `localStorage.setItem`, asserts `getAuthToken()` is null after clearing)
- `frontend/src/services/userBootstrap.test.ts` (updated — uses `setAuthToken` / `getAuthToken` for the in-memory store)
- `frontend/src/services/replayWsClient.test.ts` (updated — awaits the async `resolveReplayWsUrl` and uses `setAuthToken`)

**Notes / open items:**
- Legacy `?token=` fallback is still emitted when `VITE_WS_TICKET !== 'true'` so the FE can be shipped before / after the BE endpoint. Once the paired BE endpoint is fully rolled out, the fallback can be removed.
- Reload without a silent-refresh path forces a re-login (deferred to a follow-up per Agent E's plan).

---

### FE-L2-004 — AuthModal password `minLength` — **Done**

**Change:** Added `PASSWORD_MIN_LENGTH_REGISTER = 8` and `PASSWORD_MIN_LENGTH_LOGIN = 1` shared constants to `constants/auth.ts` and wired `AuthModal` to `minLength={mode === 'register' ? … : …}`. Register mode also gets a "At least 8 characters" hint below the input.

**Files:**
- `frontend/src/constants/auth.ts`
- `frontend/src/components/Auth/AuthModal.tsx`
- `frontend/src/components/Auth/AuthModal.test.tsx` **(new)**

**Tests added:** login mode → `minLength === 1`; register mode → `minLength === 8`.

---

### FE-L2-005 — `scanApi.ts` request shape — **Done**

**Change:** Rewrote `ScanCreateRequest`, `ScanRunResponse`, `ScanMatch`, `ScanError` types to mirror `backend/api/schemas/scan.py` exactly. Dropped the `strategy_name` field and the `ScanRequest` / `ScanResponse` names; snake_case fields (`scan_id`, `alert_count`, `duration_ms`, `scanned_pairs`, `alert_trigger`, `persisted`) are preserved verbatim on the wire.

**Files:**
- `frontend/src/services/scanApi.ts` (rewrite)
- `frontend/src/services/scanApi.test.ts` **(new)**

**Tests added:** POST body matches `ScanCreateRequest`, response snake_case fields survive typing, `getScan` URL-encodes the scan id.

---

### FE-L2-006 — `aiApi.ts` clarify/explain payloads — **Done**

**Change:** Rewrote `AiClarifyRequest`, `AiExplainRequest`, `AiTranslateResponse`, `AiExplainResponse`, and `ClarificationQuestion` to match `backend/api/schemas/ai.py`. `aiTranslate` and `aiClarify` share the discriminated union `{ status: 'ok', … } | { status: 'needs_clarification', session_id, questions }`. `aiExplain` returns `{ explanation }`.

**Files:**
- `frontend/src/services/aiApi.ts` (rewrite)
- `frontend/src/services/aiApi.test.ts` **(new)**

**Tests added:** POST body assertions for all three endpoints; discriminated-union narrowing on the translate/clarify response.

---

### FE-L2-007 — 4429 WS_LIMIT collapses to generic "connection lost" — **Done**

**Change:**
- Added `REPLAY_CLOSE_LIMIT = 4429` to `constants/replay.ts` and `WS_CLOSE_RATE_LIMITED = 4429` to `wsCloseCode.ts`.
- `classifyWsCloseKind(4429)` now returns `'rate_limited'`.
- `ReplayConnectionReason` extended with `'rate_limited'`.
- `useReplayWs.onClose` now branches on `kind === 'rate_limited'` → `store.setConnection('red', 'rate_limited')` + `showToast('Too many concurrent WebSocket connections')`.
- `useLiveCandles` shows the same toast for the live socket.

**Files:**
- `frontend/src/constants/replay.ts`
- `frontend/src/services/wsCloseCode.ts`
- `frontend/src/services/replayWsClient.ts` (via shared classifier)
- `frontend/src/hooks/useReplayWs.ts`
- `frontend/src/hooks/useLiveCandles.ts`
- `frontend/src/types/replay.ts` (widened `ReplayConnectionReason`)

**Tests added:** `replayWsClient.test.ts` and `liveWsClient.test.ts` both include the 4429 case and assert `kind === 'rate_limited'`.

---

### FE-L2-008 — WS 4401 leaves stale `sessionId` / URL query — **Done**

**Change:** Added `onUnauthorized?: () => void` to `UseReplayWsOptions`. `useReplayWs`'s `unauthorized` branch now invokes it after `notifyAuthFailure`. `useReplaySession` exposes `onUnauthorized` on its API surface — it clears `resumeAttemptedRef`, strips the `replaySession` URL param via `writeSessionParam(null)`, calls `useReplayStore.getState().reset()`, and drops replay mode. `ReplayRoot` wires `session.onUnauthorized` into `useReplayWs`.

**Files:**
- `frontend/src/hooks/useReplayWs.ts`
- `frontend/src/hooks/useReplaySession.ts`
- `frontend/src/components/Replay/ReplayRoot.tsx`

---

### FE-L2-009 — `WatchlistRoot` 401 clobbers `expired` reason — **Done**

**Change:** In the `isUnauthorized` branch of `WatchlistRoot`'s bootstrap effect the duplicate `clearStaleUser + clearLocalUserId` sequence has been removed. `apiRequest → notifyAuthFailure` is now the single writer of the auth store on 401/403; the watchlist path only drops the stale cache via `deleteWatchlistCache(userId)` and calls `setNeedsAuth()` **only** when the session hasn't already been marked `expired`. The `USER_NOT_FOUND` branch retains its full-clear + reload behaviour untouched.

**Files:**
- `frontend/src/components/Watchlist/WatchlistRoot.tsx`

---

### FE-L2-010 — `resolveWatchlistDtos` hard-fails on any unresolved symbol — **Done**

**Change:** `resolveWatchlistDtos` now returns `{ watchlists, unresolved }`. Unresolved IDs are dropped per-watchlist and reported to the caller; `WatchlistRoot` fires a soft `showToast('Some symbols could not be loaded and were hidden')` when `unresolved.length > 0`. `SymbolResolveError` is still thrown when a watchlist that started with symbols resolves to zero (indicating a real BE outage rather than a delisted pair). All internal callers of `resolveWatchlistDtos` were updated.

**Files:**
- `frontend/src/utils/watchlistNormalize.ts`
- `frontend/src/components/Watchlist/WatchlistRoot.tsx`
- `frontend/src/utils/watchlistNormalize.test.ts` (updated — previously-throw case now asserts partial results)

---

### FE-L2-011 — `resolveReplayWsUrl` appends JWT to any absolute WS URL — **Done**

**Change:** Split URL resolution into a sync `resolveReplayWsBase(wsUrl, location)` (host validation + protocol) and an async `resolveReplayWsUrl(wsUrl, location)` (delegates to `getWsConnectUrl`). Absolute `ws(s)://` URLs are accepted only when `new URL(wsUrl).host === location.host` — otherwise the client throws `Refusing to open replay WS on foreign host: …`. The same guard now protects `LiveWsClient.resolveLiveWsBase` when `VITE_LIVE_WS_URL` is set to an absolute URL.

**Files:**
- `frontend/src/services/replayWsClient.ts`
- `frontend/src/services/liveWsClient.ts`
- `frontend/src/services/replayWsClient.test.ts` (added `rejects absolute WS URLs pointing at a foreign host` + `allows same-origin absolute WS URLs`)
- `frontend/src/services/liveWsClient.test.ts` (added `resolveLiveWsBase rejects a configured foreign-host absolute URL`)

---

## Full test results

```
Test Files  51 passed (51)
     Tests  205 passed (205)
   Start at 14:56:43
  Duration  ~4.06s
```

G3 subset (`useChunkManager.test.tsx`, `replayWsClient.test.ts`, `userBootstrap.test.ts`, `chartDataWindow.test.ts`, `api.test.ts`):

```
Test Files  5 passed (5)
     Tests  27 passed (27)
```

TypeScript check (`npx tsc --noEmit`): clean.

---

## Notes for Agent G / follow-ups

- **Ticket flag rollout:** `VITE_WS_TICKET` defaults on in production and off in dev/test. The BE `POST /api/v1/ws/tickets` endpoint returns `{ticket, expires_in}` (matches FE `WsTicketResponse` typing). Legacy `?token=<jwt>` remains supported on `/ws/live` and `/ws/replay/{id}`; the flag can be flipped by env override on either side while the release soaks.
- **Reload UX:** With the in-memory JWT, a hard reload without a paired silent-refresh path forces re-authentication. This is deliberate per Agent E's plan; a follow-up refresh-token flow is out of scope for L2.
- **`LiveWsClient.connect` and `ReplayWsClient.connect` are now `async`.** External callers should treat them with `void client.connect(...).catch(...)`. `useLiveCandles` / `useReplayWs` both do this internally and surface connection errors via the same `connection = 'red'` / soft-toast paths existing tests already assert.
- **`resolveWatchlistDtos` return shape changed** from `Watchlist[]` to `{ watchlists, unresolved }`. All in-tree callers were updated in this pass; any future consumer needs the new destructure.
- **Ownership of the auth-clear pipeline** has been consolidated: `apiRequest → notifyAuthFailure` is the single writer of `session === 'expired'`. `WatchlistRoot` no longer wipes the auth store on 401; it only drops the watchlist cache and (optionally) upgrades the session to `needs_auth` when the store had no error code yet. If Agent G adds any other 401 catchers, they should follow this pattern (no duplicated `clearLocalUserId()` after `apiRequest` has run).

---

## Return-to-parent counts

- **Done:** 11 / 11 (FE-L2-001 through FE-L2-011)
- **Partial:** 0
- **Blocked:** 0
- **Test failures introduced / left:** 0
- **Tests added:** 7 new test files (`wsCloseCode.test.ts`, `wsTicketClient.test.ts`, `authToken.test.ts`, `liveWsClient.test.ts`, `scanApi.test.ts`, `aiApi.test.ts`, `AuthModal.test.tsx`); 4 existing files updated for the in-memory JWT / async WS URL contract.
- **Agent G attention:** none — all recommended solutions landed, tests are green, TS is clean.
