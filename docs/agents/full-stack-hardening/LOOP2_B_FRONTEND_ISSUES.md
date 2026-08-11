# Agent B (Loop 2) — Frontend Issues (matched to backend)

**Date:** 2026-08-11
**Repo:** `/Users/sohailmulla/projects/crypto-backtester`
**Working tree base:** as-is (uncommitted). G3 declared FE "NONE remaining"; this re-review found real gaps.
**Scope:** `frontend/src/**` (auth, services, hooks, stores, components) cross-checked against BE routers/schemas/WS handlers and `backend/docs/openapi.yaml`.

---

## Summary

Auth bootstrap, replay REST/WS control-plane, chart chunking, watchlist HTTP client, and the primary `apiRequest` error/401 pipeline generally match the current backend contracts. Silent-latest-fallback, WS 4401/4402 distinct-code handling, `/auth/me` reprove, `REGISTRATION_FAILED` fallback, and 404-as-empty guards from G1/G2/G3 are all in place and covered by tests.

However, there are **still several real, actionable mismatches or defensive gaps** the last G3 pass missed. The most important are:

- Live WS is quietly broken on the client (field-name mismatch with backend `bar`/`candle`).
- The live WS client discards close codes entirely (no 4401 auth-clear, no 4429 rate hint).
- FE stores JWT in `localStorage` and passes it via `?token=` on every WS URL — the FE side of the G-014 leak (BE-only redaction addressed).
- `scanApi.ts` and `aiApi.ts` request shapes drifted materially from the current backend schemas (whole POST bodies are wrong).
- AuthModal's `minLength={6}` password contradicts the backend's `min_length=8` register rule.
- Replay 4401 close leaves the URL param + `sessionId` in place, so re-auth walks into a 4404 dance.

Everything below is grounded in the current working tree (not the pre-G2 baseline).

---

## Issues

### FE-L2-001: Live WS candle payload field mismatch (`bar` vs `candle`) — silent breakage
- **Severity hint:** Important
- **Area:** ws / contract
- **Backend contract:** `backend/api/ws/live.py:127-134` publishes `{"type":"candle","symbol":..,"timeframe":..,"bar": bar.model_dump()}`. OpenAPI `LiveWsCandleEvent` (`backend/docs/openapi.yaml:1434-1446`) confirms `required: [type, symbol, timeframe, bar]`.
- **Frontend behavior:** `LiveWsClient.onmessage` reads `row.candle` and short-circuits when it is `!candleRaw || typeof candleRaw !== 'object'`. It also expects a boolean `incomplete` flag the backend never emits. Result: `handlers.onCandle` never fires when live WS is enabled.
- **Evidence:**
  - `frontend/src/services/liveWsClient.ts:51-79`
  - `frontend/src/hooks/useLiveCandles.ts:24-33`
  - `backend/api/ws/live.py:127-134`
  - OpenAPI `LiveWsCandleEvent` in `backend/docs/openapi.yaml:1434-1446`
- **Impact:** With `VITE_LIVE_WS=true`, chart bars never receive live updates from the backend polling loop — no visible error, just no ticks. Feature flag currently masks user-facing breakage but any operator who flips it will get a silently dead pane. This is exactly the sort of contract drift the FE hardening pass was meant to catch.

### FE-L2-002: Live WS discards close code — no 4401 / 4429 handling
- **Severity hint:** Important
- **Area:** ws / auth
- **Backend contract:** `/ws/live` closes with `4401 UNAUTHORIZED` on missing/invalid JWT and `4429 WS_LIMIT` on per-user connection cap (`backend/api/ws/live.py:77-91`). Replay WS uses the same set.
- **Frontend behavior:** `LiveWsClient` typing exposes `onClose?: () => void` (no code/reason). The socket handler is `socket.onclose = () => this.handlers.onClose?.()` — the `event.code` is dropped on the floor. `useLiveCandles` doesn't even wire `onClose`, so:
  - Expired JWT on a running chart → server closes 4401, FE never learns; user stays "logged in" from the app store's perspective until the next REST call fails.
  - Concurrent connection cap exceeded → same silence, no toast, no telemetry.
- **Evidence:**
  - `frontend/src/services/liveWsClient.ts:4-13,86-91` (no code in `onClose`)
  - `frontend/src/hooks/useLiveCandles.ts:18-41` (no `onClose` provided)
  - Compare with the correctly-handled replay path in `frontend/src/hooks/useReplayWs.ts:151-189`
- **Impact:** Live WS auth failure is a silent security/session drift — the FE will not invoke `notifyAuthFailure`, and inbound polling stops without any user indication. Live WS breach of the auth-clear contract that G-002/G3 explicitly hardened for the replay socket.

### FE-L2-003: JWT stored in `localStorage` and appended as `?token=` on every WebSocket URL
- **Severity hint:** Important
- **Area:** security / auth
- **Backend contract:** BE accepts JWT via `Authorization: Bearer` or `?token=` (`backend/api/deps.py:159-166`). G-014 shipped a `.env.example` note asking operators to redact `?token=` in access logs but treated the WS-token-in-URL as a BE-only concern.
- **Frontend behavior:**
  - `authToken.ts` persists the JWT to `window.localStorage` under `auth_token` — readable by any XSS, browser extension, or third-party script loaded into the app origin. There is no `HttpOnly` cookie / `sessionStorage` / in-memory fallback.
  - Both `replayWsClient.resolveReplayWsUrl` (line 30-46) and `liveWsClient.resolveLiveWsUrl` (line 16-27) unconditionally append `token=<jwt>` to the URL, so the JWT lands in:
    - DevTools → Network → WS entry (`url` column) and HAR exports.
    - Referer headers if the socket URL ever leaks into a document context.
    - Third-party monitoring / RUM that samples `location`-style URLs.
  - `resolveReplayWsUrl` also appends the token even when the caller passes an already-absolute `ws(s)://` URL — the token would follow a mistaken/absolute host into unknown territory (defense-in-depth failure, currently theoretical because BE returns a relative path).
- **Evidence:**
  - `frontend/src/services/authToken.ts:1-17`
  - `frontend/src/services/replayWsClient.ts:30-46`
  - `frontend/src/services/liveWsClient.ts:16-27`
  - `frontend/src/services/authSession.ts:16-35` (clear-only path)
- **Impact:** The FE side of the same leak G-014 flagged for BE — a JWT that never appears in a URL is easier to keep out of logs, traces, and history. Combined with `localStorage` retention, an XSS on this app is a full JWT theft. Suggested remediation: switch to `Sec-WebSocket-Protocol` header, or add a `POST /ws/tickets` short-lived one-shot ticket, and move the bearer store off `localStorage`.

### FE-L2-004: Register password `minLength={6}` contradicts BE `min_length=8`
- **Severity hint:** Minor (UX)
- **Area:** auth / contract
- **Backend contract:** `AuthRegisterRequest.password: str = Field(min_length=8, max_length=200)` (`backend/api/schemas/auth.py:34`).
- **Frontend behavior:** `AuthModal` password input uses `<input minLength={6} required>` for **both** login and register modes (`frontend/src/components/Auth/AuthModal.tsx:130-138`). Users typing a 6- or 7-char password in Register mode pass FE validation, submit, and get a raw pydantic 422 (`String should have at least 8 characters`) via `formatErrorMessage`, which is confusing UX.
- **Evidence:**
  - `frontend/src/components/Auth/AuthModal.tsx:128-140`
  - `backend/api/schemas/auth.py:29-40`
- **Impact:** Rejected registration attempts with a mysterious error. Trivial fix: `minLength={mode === 'register' ? 8 : 6}` or drive from a shared constant so BE + FE stay in sync.

### FE-L2-005: `scanApi.ts` request shape drifted from `ScanCreateRequest`
- **Severity hint:** Important (contract drift)
- **Area:** api / contract
- **Backend contract:** `ScanCreateRequest` requires `timeframes: list[str]` (min_length=1), `condition: dict[str, Any]`, `start`, `end`, optional `symbols: list[str] | None`, `alert_trigger: 'edge'|'level'`, `persist: bool` (`backend/api/schemas/scan.py:13-33`). Response envelope uses `scan_id` (may be `None` when `persist=false`).
- **Frontend behavior:** `ScanRequest` is `{ symbols: string[]; timeframe: string; start: number; end: number; strategy_name?: string }`:
  - Sends `timeframe` (scalar), not `timeframes` (list).
  - Never sends `condition` (required).
  - Sends `strategy_name` which the BE ignores/rejects (not in schema).
  - No caller in `frontend/src/**` invokes `runScan` yet, but the shape is exported as the public FE contract for the scan endpoint.
- **Evidence:**
  - `frontend/src/services/scanApi.ts:1-30`
  - `backend/api/schemas/scan.py:13-68`
  - `Grep` confirms zero callers today.
- **Impact:** As soon as the scan UI is wired, every POST will 422. Not caught by G3 because there's no integration test through this client.

### FE-L2-006: `aiApi.ts` clarify/explain payloads mismatched with BE
- **Severity hint:** Important (contract drift)
- **Area:** api / contract
- **Backend contract:**
  - `ClarifyRequest`: `{ session_id: str (min 1), answers: dict[str, str] (min 1) }` (`backend/api/schemas/ai.py:18-23`).
  - `ExplainRequest`: `{ strategy: dict[str, Any] }` (`backend/api/schemas/ai.py:25-28`).
- **Frontend behavior:**
  - `AiClarifyRequest = { message: string; session_id?: string }` — wrong field (`message` vs `answers`) and `session_id` is typed as optional.
  - `AiExplainRequest = { run_id?: string; context?: string }` — completely unrelated to BE `{ strategy }`.
  - `AiTranslateRequest` (`{ text }`) matches BE.
  - No FE code currently invokes `aiClarify` / `aiExplain`, but the exported types are the FE contract surface.
- **Evidence:**
  - `frontend/src/services/aiApi.ts:1-37`
  - `backend/api/schemas/ai.py:12-58`
- **Impact:** Any AI UI wiring will 422 immediately; also `getAiService` requires JWT + rate limit (`backend/api/deps.py:123-137`), so a rate-limit contract test that relied on these clients would fail before hitting `rate_limit_ai`. G2 confirmed OpenAPI removed `/auth/claim`; it did not audit the AI client shapes.

### FE-L2-007: Replay + Live WS 4429 (`WS_LIMIT`) collapses to a generic "connection lost" UX
- **Severity hint:** Minor
- **Area:** ws / UX
- **Backend contract:** `deps.acquire_ws_slot` refuses at `WS_MAX_CONNECTIONS_PER_USER` and closes the socket with `code=4429 reason="WS_LIMIT"` (`backend/api/deps.py:140-149`; used by both `ws/replay.py:120-124` and `ws/live.py:87-91`).
- **Frontend behavior:** `replayWsClient.closeKind` only recognises 4401 / 4402 / 4404 / 1000 / 1001 — every other numeric code (including 4429) becomes `'error'`. `useReplayWs` on `kind === 'error'` shows a generic `showToast('Replay connection lost')`. No differentiation. `LiveWsClient` never surfaces the code at all (see FE-L2-002), so the same 4429 close is fully invisible.
- **Evidence:**
  - `frontend/src/services/replayWsClient.ts:48-62`
  - `frontend/src/hooks/useReplayWs.ts:173-178`
  - `backend/api/deps.py:140-149`, `backend/api/ws/replay.py:120-124`, `backend/api/ws/live.py:87-91`
- **Impact:** Users hitting the per-user WS cap don't know why the replay went red; support burden. Trivial add: `REPLAY_CLOSE_LIMIT = 4429` and a distinct UX branch.

### FE-L2-008: On WS 4401, replay `sessionId` + URL param stay set → 4404 cascade after re-auth
- **Severity hint:** Minor
- **Area:** ws / auth / replay
- **Backend contract:** 4401 means the WS's token was rejected. Once the FE re-authenticates as the same user, the existing session should still be reachable; as a different user the BE returns 4404 (owner mismatch is `NotFoundError` → close 4404).
- **Frontend behavior:** `useReplayWs`'s `unauthorized` branch calls `notifyAuthFailure('UNAUTHORIZED')`, `setPhase('paused')`, and `setError('Authentication required')` (`frontend/src/hooks/useReplayWs.ts:155-161`). It does **not** clear `sessionId`, `wsUrl`, or the `replaySession` URL query. When the user signs back in, `useReplaySession`'s URL-resume `useEffect` re-issues `beginConnect(sessionFromUrl, ...)` and `getReplaySession` (`frontend/src/hooks/useReplaySession.ts:214-276`). If auth returned a different user, the REST GET 404s (or the WS closes 4404) and the UX ends at "Replay session not found — pick a bar to start again".
- **Evidence:**
  - `frontend/src/hooks/useReplayWs.ts:151-189`
  - `frontend/src/hooks/useReplaySession.ts:214-276`
  - `backend/api/ws/replay.py:32-118`
- **Impact:** UX regression around re-auth: the residual URL query + error message ("Authentication required") both linger in the store even after the modal is dismissed, until either the next auto-reconnect fires 4404 (see amber-banner branch) or the user manually navigates. A defensive `reset()` on `unauthorized` (or dropping the `replaySession` URL param) would prevent the double failure.

### FE-L2-009: `WatchlistRoot` 401/403 handler wipes the "expired" auth reason set by `apiRequest`
- **Severity hint:** Minor
- **Area:** auth / watchlist
- **Backend contract:** `/users/{id}/watchlists` returns 401 (invalid JWT) or 403 (`ForbiddenError` from `require_same_user`) — both surfaced as `ApiError` on the FE.
- **Frontend behavior:** `apiRequest` already calls `notifyAuthFailure(code)` on 401/403 outside `AUTH_EXEMPT_PREFIXES`, which sets `session === 'expired'` and remembers the code. `WatchlistRoot` then catches the same error, calls `clearStaleUser(userId)` → `clearLocalUserId()` which resets the entire auth store to `{ session: 'unknown', lastErrorCode: null }` (`frontend/src/services/userBootstrap.ts:224-228`, `frontend/src/stores/authStore.ts:59-67`) and *then* calls `useAuthStore.getState().setNeedsAuth()`. Final state is `needs_auth` with `lastErrorCode: null` — the `UNAUTHORIZED`/expired signal from `notifyAuthFailure` is lost, so the AuthModal shows the generic "Sign in" copy instead of the "Session expired" variant.
- **Evidence:**
  - `frontend/src/components/Watchlist/WatchlistRoot.tsx:157-198`
  - `frontend/src/services/authSession.ts:16-35`
  - `frontend/src/services/userBootstrap.ts:220-228`
  - `frontend/src/stores/authStore.ts:50-67`
  - `frontend/src/components/Auth/AuthModal.tsx:23-27` (uses `session === 'expired'` to switch copy)
- **Impact:** Users whose token expired mid-session see the "Sign in" first-time UX rather than "Session expired", which G2-001/G3 was supposed to close. Order-of-operations bug rather than functional break, but it defeats the intended copy contract.

### FE-L2-010: `resolveWatchlistDtos` hard-fails the whole refresh on any unresolved symbol id
- **Severity hint:** Minor (durability)
- **Area:** api / watchlist
- **Backend contract:** BE watchlist responses can contain symbols that are inactive or missing from the current catalog (e.g., a delisted pair). `GET /symbols/{symbolId}` returns 404 for unknown symbols.
- **Frontend behavior:** `resolveWatchlistDtos` first pulls the *active-only* catalog (`searchSymbols('')`), then for any missing ID it falls back to `getSymbol(id)`. If even one ID stays unresolved (delisted → 404 or inactive filter drops it), it throws `SymbolResolveError`, and `WatchlistRoot` treats the whole refresh as `error` (`frontend/src/components/Watchlist/WatchlistRoot.tsx:157-198`). The panel keeps the cached rows if `keepRows` is true but otherwise the entire watchlist fails to render.
- **Evidence:**
  - `frontend/src/utils/watchlistNormalize.ts:99-133`
  - `frontend/src/services/chartDataAdapter.ts:93-103` (`searchSymbols` sets `active_only: 'true'`)
  - `frontend/src/components/Watchlist/WatchlistRoot.tsx:195-198`
- **Impact:** Any single stale ID nukes the entire panel — either drop the offending IDs with a warning toast, or fetch by `active_only=false` for the fallback path. Also relevant to the ownership UX Agent B was asked to review: the failure mode is indistinguishable from a hard 500.

### FE-L2-011: `resolveReplayWsUrl` blindly attaches the JWT to any absolute `ws(s)://` URL supplied by the backend
- **Severity hint:** Minor (defense-in-depth)
- **Area:** ws / auth
- **Backend contract:** `POST /replay/sessions` currently returns a relative `ws_url = /ws/replay/{id}` (`backend/api/routers/replay.py:39-43`). FE also fabricates `ws_url = /ws/replay/{sessionId}` when resuming from the URL query.
- **Frontend behavior:** `resolveReplayWsUrl(wsUrl)` early-returns `appendToken(wsUrl)` when the string starts with `ws://` / `wss://`. If a future BE change (or a malicious/misconfigured response) ever sends `wss://third-party.example.com/x`, the FE will happily deliver the JWT to that origin.
- **Evidence:** `frontend/src/services/replayWsClient.ts:30-46`
- **Impact:** Theoretical today (BE only emits relative paths); the code is a latent footgun. Consider asserting host equality with `location.host`, or accepting only relative paths and constructing the origin locally.

---

## Clean areas (brief)

- **Central `apiRequest` error envelope + 401/403 auth-clear** (`frontend/src/services/api.ts`, `authSession.ts`) — correctly exempts `/auth/login` and `/auth/register`, only clears when a token was actually presented, extracts BE `error.code`, and has coverage in `api.test.ts`.
- **`userBootstrap` DEV auto-provision** now handles `REGISTRATION_FAILED` (G2-001) plus legacy `EMAIL_EXISTS`, `AUTH_FAILED`, with explicit test coverage; `/auth/me` reprove replaces the removed `GET /users`.
- **`replayWsClient` close-code mapping (4401 / 4402 / 4404)** matches BE constants and drives distinct `useReplayWs` UX branches (auth clear vs amber-superseded vs amber-not-found).
- **`useChunkManager` prefetch guard** uses `hasCoverage` + `isRangedFallbackResponse` + `reachedEarliestRef`, matching FE-010/011 and BE's `empty: true` contract — no more infinite prefetch loop when the ranged window is empty.
- **`chartDataAdapter` runId overlays** propagate `runId` through the unified `/chart-data` endpoint (with `Authorization` via `apiRequest`), matching the BE ownership-404 pathway.
- **Backtest / watchlist HTTP clients** are aligned with `by_alias`/snake response bodies and correctly encode symbol IDs (`BTC%2FUSDT`) — verified by `backtestApi.test.ts` and `watchlistApi.test.ts`.

---

## Remaining issue count

**11**

IDs (one-line):

- FE-L2-001 — Live WS `bar` vs `candle` field mismatch silently breaks live candles.
- FE-L2-002 — `LiveWsClient.onClose` drops the close code; no 4401/4429 handling.
- FE-L2-003 — JWT in `localStorage` + WS `?token=` query leaks bearer into DevTools/history/HAR (FE half of G-014).
- FE-L2-004 — `AuthModal` password `minLength={6}` contradicts BE register `min_length=8`.
- FE-L2-005 — `scanApi` posts `timeframe` (scalar) and no `condition`; BE requires `timeframes: list[str]` + `condition`.
- FE-L2-006 — `aiApi` clarify/explain payloads don't match BE (`answers` / `strategy` missing).
- FE-L2-007 — Replay & Live WS 4429 (`WS_LIMIT`) collapse to generic "connection lost" UX.
- FE-L2-008 — Replay 4401 leaves `sessionId` + URL query set → 4404 cascade after re-auth; residual "Authentication required" error sticks.
- FE-L2-009 — `WatchlistRoot` 401 path clobbers the `expired` reason set by `apiRequest`, so AuthModal shows "Sign in" instead of "Session expired".
- FE-L2-010 — `resolveWatchlistDtos` hard-fails the entire watchlist refresh on any single unresolved symbol id.
- FE-L2-011 — `resolveReplayWsUrl` appends the JWT to any absolute `ws(s)://` URL from the BE (latent footgun).
