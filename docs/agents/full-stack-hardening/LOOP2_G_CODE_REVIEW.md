# Agent G (Loop 2) — Code Review

**Date:** 2026-08-11
**Repo:** `/Users/sohailmulla/projects/crypto-backtester`
**Inputs:**
- `docs/agents/full-stack-hardening/LOOP2_F_BACKEND_IMPLEMENTATION.md`
- `docs/agents/full-stack-hardening/LOOP2_H_FRONTEND_IMPLEMENTATION.md`
- `docs/agents/full-stack-hardening/LOOP2_A_BACKEND_ISSUES.md`
- `docs/agents/full-stack-hardening/LOOP2_B_FRONTEND_ISSUES.md`
- `docs/agents/full-stack-hardening/LOOP2_C_SEVERITY_DEPENDENCY.md`

## Verdict: READY

All 31 issues (20 backend + 11 frontend) are addressed in code and covered by
tests. The requested spot-checks (V018 CASCADE, WS ticket flow, rate limiter,
async LiveWsClient.connect, `resolveWatchlistDtos` return-shape callers,
authToken in-memory drain, scanApi/aiApi payload shapes, OpenAPI security
matrix) all pass. Backend suite (67 tests) and frontend suite (51 files / 205
tests) run clean; `npx tsc --noEmit` is silent.

No regressions or new defects that block merge. Three cosmetic /
documentation-drift observations are captured under **New defects found**
(non-blocking, worth catching before the next release).

## Summary

- **Verdict:** READY
- **Remaining critical/important issues:** 0
- **Remaining minor issues:** 0
- **New defects found:** 3 (all doc / cosmetic; none blocking)
- **Backend tests (in-scope subset):** 67 passed, 0 failed
- **Frontend tests:** 205 passed, 0 failed
- **`npx tsc --noEmit`:** clean

## Issue disposition (be comprehensive)

### Backend — BE-L2-001…020 + BE-for-FE-L2-003

| ID | Status | Evidence |
|----|--------|----------|
| BE-L2-001 | Fixed | New `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql` drops and re-adds `backtest_runs_user_id_fkey` with `ON DELETE CASCADE` (lines 8-15). Test `test_v018_backtest_runs_fk_uses_on_delete_cascade` asserts the SQL contains both `backtest_runs_user_id_fkey` and `on delete cascade`. |
| BE-L2-002 | Fixed | `backend/api/ws/live.py:176-177` sets `db_conn.autocommit = True` before `websocket.accept()`, eliminating the "poisoned by first failure" transaction. `_latest_bars` (`live.py:44-83`) now returns `(results, invalid_keys)` and `poll_once` (`live.py:125-169`) emits a one-shot `INVALID_SYMBOL` error frame per bad key without tearing the socket. `test_live_ws_subscribe_pushes_candle` updated to the new `(bars, [])` tuple. |
| BE-L2-003 | Fixed | `backend/docs/openapi.yaml` now declares `security: [{ bearerAuth: [] }]` on `/auth/me` (line 422), `/users/{user_id}` GET/PATCH/DELETE (lines 490,511,540), `/backtest` and `/backtest/{run_id}(/trades)` (lines 729,756,782), `/scan` (line 813) and the newly-documented `/scan/{scan_id}` GET (line 838), all `/ai/*` (lines 868,903,935), `/replay/sessions*` (lines 960,987,1006), and `/ws/tickets` (line 1033). `POST /users` and `GET /users` are declared `410 Gone` with `code: GONE` examples (lines 434-483). Central `Unauthorized`, `Forbidden`, and `RateLimited` responses are defined once (lines 1192-1238) and referenced consistently. |
| BE-L2-004 | Fixed | OpenAPI `x-websocket.replay` now documents `4401 UNAUTHORIZED`, `4402 SUPERSEDED`, `4404 REPLAY_NOT_FOUND`, and `4429 WS_LIMIT` as distinct application close codes (lines 1069-1076). Matches BE constants at `backend/api/ws/replay.py:33-35`. |
| BE-L2-005 | Fixed | OpenAPI `x-websocket.live` (lines 1107-1130) now declares JWT-required auth (ticket-preferred), documents the per-user `4429 WS_LIMIT`, the one-shot `INVALID_SYMBOL` error frame, and links to the `LiveWsCandleEvent` schema. No more "Public in v1" wording. |
| BE-L2-006 | Fixed | `backend/api/schemas/replay.py:45` sets `model_config = ConfigDict(extra="forbid")`; the `user_id` field is gone. `backend/api/routers/replay.py` derives ownership strictly from `current.id`. Test `test_replay_session_create_rejects_user_id_field` asserts pydantic ValidationError. |
| BE-L2-007 | Fixed | `backend/api/deps.py:67-86` — `get_optional_user` catches `UnauthorizedError` and returns `None`. `backend/api/routers/chart_data.py:42-43` enforces `if run_id is not None and current is None: raise UnauthorizedError()`. Two tests confirm behaviour: `test_chart_data_stale_token_public_window_still_ok` (public window with bad token → 200) and `test_chart_data_run_id_without_auth_fails_closed` (runId without JWT → 401). |
| BE-L2-008 | Fixed | `backend/api/services/auth_service.py:33-48` narrows `UniqueViolation` via `_extract_constraint_name`. Email-uniqueness constraints keep the anti-enumeration `REGISTRATION_FAILED`; everything else emits `PROVISIONING_CONFLICT` with `logger.exception`. Same pattern replicated in `backend/api/services/user_service.py:21-100`. Test `test_register_provisioning_conflict_maps_to_distinct_code` covers the watchlist-default collision path. |
| BE-L2-009 | Fixed | New `backend/api/rate_limiter.py` implements the shared façade with `InProcessRateLimiter` (bounded ≤10k tracked keys via `_trim_locked`, sliding-window `check_rpm`, atomic `acquire_slot`/`release_slot`, per-lock thread safety) and a clean Redis plug-point (`_NullRedisRateLimiter` + factory in `get_rate_limiter`). `deps.py` wraps callers with `check_ai_rpm`, `acquire_ws`, `release_ws`, and `check_anonymous_register`. `REDIS_URL` selects the Redis path when the `redis` package is importable; fallback logs once. Tests `test_in_process_rpm_denies_over_limit` and `test_in_process_slot_acquire_release_symmetric` prove behaviour. |
| BE-L2-010 | Fixed | `backend/api/routers/auth.py:29-33` runs `rate_limit_anonymous_ip` as a FastAPI dependency BEFORE body validation; `rate_limit_register_email(body.email)` fires inside the router after Pydantic parses the body. `deps.py:_client_ip` respects `TRUST_PROXY_HEADERS` (`settings.trust_proxy_headers()`) so XFF is only honoured behind a scrubbing proxy. Test `test_register_ip_rate_limit_returns_429` proves 429 at the 3rd request when the limit is 2. |
| BE-L2-011 | Fixed | `backend/api/auth.py:51-53` precomputes `_DUMMY_BCRYPT_HASH` at import time. `verify_password` always runs `bcrypt.checkpw` against the dummy hash when `password_hash is None`. `auth_service.py:141-154` passes `candidate_hash = user.password_hash if user is not None else None`. Test `test_login_unknown_email_still_runs_bcrypt` asserts `bcrypt.checkpw` is called on the unknown-email path. |
| BE-L2-012 | Fixed | `backend/api/ws/live.py:106-260` and `backend/api/ws/replay.py:123-270` both wrap `websocket.accept()` and the poll/main loop inside a `try/finally` that releases the WS slot exactly once via `slot_released` guard. Any exception after `acquire_ws_slot` returns to the `finally` and releases. |
| BE-L2-013 | Fixed | `backend/api/ws/replay.py:37-40` — `_active_lock = asyncio.Lock()` guards both the check-then-supersede-then-store window (lines 134-136) and the disconnect cleanup (lines 265-267). Concurrent connects to the same `session_id` cannot both survive. |
| BE-L2-014 | Fixed | `backend/api/services/scan_service.py:175-201` — persist failures now `logger.exception`, set `persisted=False`, and populate `persist_error="PERSIST_FAILED"` on the response envelope. Schema at `backend/api/schemas/scan.py:69` adds `persist_error: str \| None = None`. Test `test_post_scan_persist_failure_reports_persist_error` verifies both flags. OpenAPI schema `ScanRunResponse` at `openapi.yaml:2322-2329` documents the field. |
| BE-L2-015 | Fixed | New `backend/data/migrations/sql/V019__data_gaps_no_overlap.sql` creates `btree_gist`, pre-cleans overlapping open rows, and adds `EXCLUDE USING gist (symbol =, timeframe =, tstzrange(start_ts, end_ts, '[]') &&) WHERE (status='open')`. `backend/data/gaps.py:205-218` catches `psycopg.errors.ExclusionViolation` from `create_gap` as a benign race and logs at debug. Test `test_reconcile_gaps_tolerates_exclusion_violation_race` and migrator test `test_v019_data_gaps_no_overlap_uses_exclude_gist` cover both. |
| BE-L2-016 | Fixed | `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql:3-13` header carries the destructive-delete WARNING and points at the runbook. New `backend/ops/scripts/archive_orphan_backtests.sql` is an idempotent archive helper. New `docs/runbooks/V017_backfill.md` covers pre-flight archive, apply, and post-fact recovery flows. |
| BE-L2-017 | Fixed | `backend/ai/translate.py:110-115` and `171-178` — `SESSION_NOT_FOUND` no longer echoes the caller-supplied `session_id`; message is generic (`"Unknown or expired session"`). The id is still logged for ops. Test `test_unknown_session_raises` asserts `caller_supplied not in exc_info.value.message`. |
| BE-L2-018 | Fixed | Grouped with BE-L2-017; OpenAPI `POST /ai/clarify` already documents `404` (`openapi.yaml:922-923`) with the generic `SESSION_NOT_FOUND` example (line 1273-1275). |
| BE-L2-019 | Fixed | `backend/api/routers/users.py:23-39` returns 410 Gone with `{"error":{"code":"GONE",...}}` pointing at `/auth/register`. OpenAPI `openapi.yaml:434-461` marks the operation `deprecated: true` and documents the 410 envelope. Test `test_post_users_returns_410_gone` locks the code and body. |
| BE-L2-020 | Fixed | `backend/data/migrations/migrator.py:25-30,110-116,144-153` uses `pg_advisory_lock(hashtext(current_database()), 0x0000_A1C9)` and the matching unlock, so multi-DB clusters no longer serialize migrations. Test `test_migrator_advisory_lock_is_scoped_per_database` inspects the source string. |
| BE-for-FE-L2-003 | Fixed | New `backend/api/routers/ws_tickets.py` mints via `POST /api/v1/ws/tickets` (JWT-required, 201). New `backend/api/services/ws_ticket_service.py` implements the in-process TTL cache with `secrets.token_hex(32)` (64 hex chars — see note under **New defects**), thread-safe `issue`/`consume` (single-use pop), and pruning. `backend/api/deps.py:207-245` — `resolve_ws_user` prefers `?ticket=` and falls back to legacy `?token=` / Authorization with an `ws_bearer_in_url` info-log. Wired into both WS handlers. Tests: `test_post_ws_tickets_requires_jwt_and_returns_ticket`, `test_ws_ticket_service_expiry_returns_none`, `test_ws_ticket_service_unknown_returns_none`. |

### Frontend — FE-L2-001…011

| ID | Status | Evidence |
|----|--------|----------|
| FE-L2-001 | Fixed | `frontend/src/services/liveWsClient.ts:65-89` reads `row.bar` (not `row.candle`), drops shorthand fallbacks and the phantom `incomplete` flag. `frontend/src/hooks/useLiveCandles.ts:31-36` no longer guards on `incomplete`. Test `reads row.bar and emits an OHLCVBar payload` + `ignores legacy row.candle payloads` in `frontend/src/services/liveWsClient.test.ts`. |
| FE-L2-002 | Fixed | `frontend/src/services/liveWsClient.ts:12` — `onClose` receives `{ code, reason, kind }` via the shared `classifyWsCloseKind`. `frontend/src/hooks/useLiveCandles.ts:37-44` wires `kind === 'unauthorized'` → `notifyAuthFailure('UNAUTHORIZED')` + toast, and `kind === 'rate_limited'` → dedicated toast. Test `surfaces close.code via onClose with the shared kind classifier` covers 4401/4429/1000. |
| FE-L2-003 | Fixed | `frontend/src/services/authToken.ts` — in-memory `inMemoryToken` with one-shot `drainLegacyStorage()` on module init that reads and then removes `localStorage['auth_token']`. `setAuthToken` / `clearAuthToken` also strip any lingering storage residue. `frontend/src/services/wsTicketClient.ts` — `isWsTicketAuthEnabled()` (prod default on, dev/test off, env-overridable via `VITE_WS_TICKET`), `getWsTicket()` POSTs to `/ws/tickets`, `getWsConnectUrl` appends `?ticket=` when enabled or `?token=` fallback. `LiveWsClient.connect` and `ReplayWsClient.connect` are now `async` and await the URL builder. Callers (`useLiveCandles`, `useReplayWs`) use `void client.connect(...).catch(...)`. Tests: `wsTicketClient.test.ts` (7), `authToken.test.ts` (4). |
| FE-L2-004 | Fixed | `frontend/src/constants/auth.ts:10-11` exports `PASSWORD_MIN_LENGTH_REGISTER = 8` and `PASSWORD_MIN_LENGTH_LOGIN = 1`. `frontend/src/components/Auth/AuthModal.tsx:137-141,149` uses the mode-driven minLength and renders "At least 8 characters" in register mode. Test `AuthModal.test.tsx` covers both mode values and asserts `PASSWORD_MIN_LENGTH_REGISTER === 8`. |
| FE-L2-005 | Fixed | `frontend/src/services/scanApi.ts` rewritten — `ScanCreateRequest` has `timeframes: string[]`, `condition: Record<string, unknown>`, optional `symbols`, `alert_trigger`, `persist`. `ScanRunResponse` preserves snake_case (`scan_id`, `alert_count`, `duration_ms`, `scanned_pairs`, `alert_trigger`, `persisted`) and matches BE schema. Old `strategy_name` gone. Tests in `scanApi.test.ts` (3) assert request-body wire shape, snake_case pass-through, and URL encoding. |
| FE-L2-006 | Fixed | `frontend/src/services/aiApi.ts` — `AiClarifyRequest = { session_id, answers }`, `AiExplainRequest = { strategy }`, discriminated union response type for translate/clarify (`{ status: 'ok' \| 'needs_clarification' }`). Matches `backend/api/schemas/ai.py` exactly. Tests in `aiApi.test.ts` (3) exercise all three endpoints and the discriminated union narrowing. |
| FE-L2-007 | Fixed | `frontend/src/services/wsCloseCode.ts:15` — `WS_CLOSE_RATE_LIMITED = 4429`; `classifyWsCloseKind` returns `'rate_limited'`. `frontend/src/constants/replay.ts:20` — `REPLAY_CLOSE_LIMIT = 4429`. `frontend/src/types/replay.ts:24-30` widens `ReplayConnectionReason` with `'rate_limited'`. `frontend/src/hooks/useReplayWs.ts:179-183` and `frontend/src/hooks/useLiveCandles.ts:41-43` both show the dedicated toast. `replayWsClient.test.ts` and `liveWsClient.test.ts` both cover the 4429 branch. |
| FE-L2-008 | Fixed | `frontend/src/hooks/useReplayWs.ts:14-15,146-167` — `UseReplayWsOptions.onUnauthorized` runs after `notifyAuthFailure`. `frontend/src/hooks/useReplaySession.ts:72-77` — `onUnauthorized` clears `resumeAttemptedRef`, strips `?replaySession=` via `writeSessionParam(null)`, calls `useReplayStore.getState().reset()`, and drops replay mode. `frontend/src/components/Replay/ReplayRoot.tsx:25` wires `session.onUnauthorized` into `useReplayWs`. No more 4404 cascade after re-auth. |
| FE-L2-009 | Fixed | `frontend/src/components/Watchlist/WatchlistRoot.tsx:178-196` — the `isUnauthorized` branch drops only the watchlist cache and calls `setNeedsAuth()` *only* if the auth store isn't already `expired`. `clearStaleUser` + `clearLocalUserId` are no longer called on 401/403 (they still run on 404 `USER_NOT_FOUND`). `apiRequest → notifyAuthFailure` remains the single writer of `session === 'expired'` + `lastErrorCode`. |
| FE-L2-010 | Fixed | `frontend/src/utils/watchlistNormalize.ts:17-21,80-151` — `resolveWatchlistDtos` returns `{ watchlists, unresolved }`. Unresolved IDs are dropped per-watchlist and reported; `SymbolResolveError` is only thrown when a watchlist that started with symbols resolves to zero. `WatchlistRoot.tsx:156-168,309-315` surfaces the soft toast. All in-tree callers (`WatchlistRoot`, tests) updated. |
| FE-L2-011 | Fixed | `frontend/src/services/replayWsClient.ts:27-51` splits sync `resolveReplayWsBase` (host validation on absolute `ws(s)://`) from async `resolveReplayWsUrl` (delegates to `getWsConnectUrl`). Same-host absolute URLs pass; foreign-host ones throw `Refusing to open replay WS on foreign host: …`. `frontend/src/services/liveWsClient.ts:16-32` mirrors the guard for `VITE_LIVE_WS_URL`. Tests `rejects absolute WS URLs pointing at a foreign host`, `allows same-origin absolute WS URLs` in both client test files. |

## Requested spot-checks

- **V018 CASCADE semantics** — verified. V018 rewrites `backtest_runs_user_id_fkey` to `ON DELETE CASCADE`. No other delete paths depend on the old `SET NULL` action; `queries.DELETE_USER` triggers the cascade, `replay_sessions`/`scan_runs`/`watchlists` already have their own cascades, and V017's `NOT NULL` invariant is preserved. The archive helper is a pre-flight-only tool (no runtime dependency).
- **WS ticket flow: BE mint → FE fetch → connect URL** — verified end-to-end.
  - BE: `POST /api/v1/ws/tickets` (JWT-required) mints via `WsTicketService.issue` → returns `{ ticket, expires_in }`. Ticket is stored in a thread-safe in-process TTL cache and consumed atomically (`_store.pop`) so the same ticket can never authorise twice.
  - FE: `getWsConnectUrl(base)` calls `getWsTicket()` immediately before each WS connect and appends `?ticket=<value>`. Ticket is not cached.
  - No race: the ticket lives in the store between mint and first consume; a WS reconnect requires a fresh mint. The legacy `?token=<jwt>` path is still accepted for one release with an `ws_bearer_in_url` audit log.
- **Rate limiter correctness (in-process, Redis plug-point)** — verified. `InProcessRateLimiter` uses a `threading.Lock` around both hits and slots, drops empty deques, and caps tracked keys at 10k. `check_rpm`, `acquire_slot`, `release_slot`, and `slot_count` behave as expected under the test suite. `_NullRedisRateLimiter` is a stub — the factory selects it only when `settings.redis_url()` is set AND `import redis` succeeds; otherwise it falls back to in-process with a warn-once. Documented multi-worker caveat is called out in code comments and in the Agent H handoff.
- **`LiveWsClient` async connect caller updates** — verified. `useLiveCandles` (`.then` after `connect`, `client.subscribe` after connect resolves, cancellation flag + `client.close()` on unmount), and `LiveWsClient.test.ts` uses `void client.connect(...)` + `waitForSocket` polling. No synchronous callers remain.
- **`resolveWatchlistDtos` return shape callers updated everywhere** — verified. Grep for `resolveWatchlistDtos` shows only `WatchlistRoot.tsx` (three call sites: `loadCanonicalWatchlists`, `createWatchlist` fallback, `addSymbolToSelected` fallback), the utility itself, and its test. All three destructure `{ watchlists, unresolved }` or accept `WatchlistResolveResult` and use `.watchlists[0]` for single-DTO calls.
- **`authToken` in-memory drain (no double-drain, no race)** — verified. `drainLegacyStorage()` runs exactly once on module import (module singleton is idempotent). `setAuthToken` and `clearAuthToken` also remove any legacy `localStorage` residue in case the module was loaded before the storage key was written. `resetAuthTokenForTests` is a test-only shortcut that only clears `inMemoryToken` (tests use `setAuthToken` to install their own value).
- **`scanApi` / `aiApi` payload shapes match current BE schemas** — verified.
  - `ScanCreateRequest` matches `backend/api/schemas/scan.py:13-33` exactly.
  - `ScanRunResponse` matches `backend/api/schemas/scan.py:54-69` — note the newly added `persist_error` field on the BE side is *not* mirrored on the FE type (see **New defects found #1** below; non-blocking because no FE consumer today).
  - `AiClarifyRequest = { session_id, answers }` matches `ClarifyRequest`.
  - `AiExplainRequest = { strategy }` matches `ExplainRequest`.
  - `AiTranslateResponse` discriminated union matches `TranslateOkResponse` / `TranslateClarifyResponse`.
- **OpenAPI security matrix completeness** — verified. Grep for `security:` and `bearerAuth` shows the block is present on every protected route: `/auth/me`, `/users/{user_id}` GET/PATCH/DELETE, `/users` GET (410), `/users/{user_id}/watchlists*`, `/backtest*` (POST/GET/GET trades), `/scan` POST + `/scan/{scan_id}` GET, `/ai/translate|clarify|explain`, `/replay/sessions*`, `/ws/tickets`, and both WebSocket handshakes (`x-websocket.replay` and `x-websocket.live`). `/chart-data` correctly declares `security: [{bearerAuth: []}, {}]` (optional bearer). Public endpoints (`meta/*`, `symbols/*`, `candles/*`, `indicators*`, `/auth/register`, `/auth/login`) do not declare `security:`. Central `Unauthorized`/`Forbidden`/`RateLimited` responses live under `components.responses`.

## New defects found (all non-blocking / cosmetic)

1. **`WsTicketResponse` documentation says "128 hex chars" but the value is 64 hex chars.**
   `secrets.token_hex(32)` returns 32 bytes = 64 hex characters (the test at `backend/tests/api/test_ws_tickets.py:62` correctly asserts `len(ticket) == 64`). Three documentation locations claim 128:
   - `backend/api/schemas/ws_tickets.py:13` — `Field(description="Opaque single-use ticket (128 hex chars).")`
   - `backend/api/services/ws_ticket_service.py:61` — docstring says "128 hex chars"
   - `backend/docs/openapi.yaml:2337` — `description: Opaque single-use ticket (128 hex chars from `secrets.token_hex(32)`).` (the example next to it *is* 64 chars, so the description contradicts the example)
   No security impact — value is still 128 bits of entropy either way — but generated SDKs might over-validate. One-liner fix.

2. **OpenAPI `ReplaySessionCreate` description is out-of-date w.r.t. `extra="forbid"`.**
   `backend/docs/openapi.yaml:1884-1887` says: *"`user_id` was removed in BE-L2-006 — the JWT subject owns every session. Sending it is ignored today and may return 422 in a future release."* With `extra="forbid"` on the pydantic model, sending `user_id` returns 422 **now** (verified by `test_replay_session_create_rejects_user_id_field`). The description should say "returns 422" rather than "may return 422 in a future release".

3. **FE `ScanRunResponse` type is missing the new `persist_error` field.**
   `backend/api/schemas/scan.py:69` adds `persist_error: str \| None = None`. OpenAPI is updated (line 2322-2329), but `frontend/src/services/scanApi.ts:45-59` does not include the field on the `ScanRunResponse` interface. No FE consumer today (Agent B confirmed zero callers of `runScan`), so this doesn't break anything, but any future UI that inspects the persist result will need the field added. Trivial two-line fix.

None of the above block the release cutover.

## Test run results

### Backend (in-scope subset requested by Agent G brief)

```
cd backend && APP_ENV=dev AI_CLARIFY_STORE=memory .venv/bin/python -m pytest \
  tests/api/test_auth.py tests/api/test_settings.py tests/api/test_scan.py \
  tests/api/test_backtest.py tests/api/test_chart_data.py tests/api/test_replay_ws.py \
  tests/api/test_live_ws.py tests/api/test_users_watchlists.py tests/api/test_ai.py -q
```

Result: **67 passed, 1 warning in 2.76s.** No failures. (The single warning is
the pre-existing `starlette.testclient` httpx-vs-httpx2 deprecation notice —
unrelated to this loop.)

### Frontend

```
cd frontend && npm test -- --run
```

Result: **51 test files, 205 tests passed** in ~4.75s. Includes the seven new
files added by Agent H (`wsCloseCode.test.ts`, `wsTicketClient.test.ts`,
`authToken.test.ts`, `liveWsClient.test.ts`, `scanApi.test.ts`, `aiApi.test.ts`,
`AuthModal.test.tsx`) and the four updated files (`api.test.ts`,
`userBootstrap.test.ts`, `replayWsClient.test.ts`, `watchlistNormalize.test.ts`).

### TypeScript

```
cd frontend && npx tsc --noEmit
```

Result: **clean** (only unrelated `npm warn Unknown env config "devdir"` output).

## Remaining issues (count + IDs)

**Remaining critical/important:** 0
**Remaining minor:** 0
**Remaining IDs from A/B:** none — every BE-L2-001..020, BE-for-FE-L2-003, and
FE-L2-001..011 issue is fixed in code and covered by at least one test.

The three "New defects found" items are cosmetic documentation drift only and
do not fall under the A/B loop-2 issue list; they can be swept in a follow-up
tidy pass if desired.
