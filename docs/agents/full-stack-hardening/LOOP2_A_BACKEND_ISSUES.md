# Agent A (Loop 2) — Backend + Database Issues

## Summary

Re-reviewed the current working tree against G3's "NONE remaining" claim. The auth / ownership / fail-closed matrix is largely holding, but I found one **critical** schema-integrity bug that will silently break `DELETE /users/{id}` in any environment that has ever run a backtest, a permanent live-WS failure mode on the shared DB connection, and several **important** OpenAPI / API-contract drifts (including the very close-code alignment G3 asserted was fixed). Multiple secondary hardening gaps (rate-limit correctness under multi-worker, register unique-constraint over-matching, timing side-channel on login, misleading `user_id` fields) are also still present.

## Issues

### BE-L2-001: V008 `ON DELETE SET NULL` conflicts with V017 `NOT NULL` — user delete will fail
- Severity hint: **Critical**
- Area: db / migrations / api
- Evidence:
  - `backend/data/migrations/sql/V008__backtest_runs.sql:17` — `user_id UUID REFERENCES app.users (id) ON DELETE SET NULL`
  - `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql:6` — `ALTER COLUMN user_id SET NOT NULL` (does **not** re-declare or alter the FK action)
  - `backend/api/routers/users.py:84` calls `_service.delete_user` which issues `DELETE app.users WHERE id = %s` (see `queries.DELETE_USER`)
- Impact: When Postgres attempts to enforce the `ON DELETE SET NULL` referential action on a `NOT NULL` column, it raises `null value in column "user_id" of relation "backtest_runs" violates not-null constraint`. Any authenticated user who has ever run a backtest can no longer be deleted — `DELETE /api/v1/users/{user_id}` returns HTTP 500 and the account persists (even though the caller expected 204). This also blocks GDPR-style account teardown.
- Repro/notes: fix by adding `ALTER TABLE app.backtest_runs DROP CONSTRAINT backtest_runs_user_id_fkey, ADD CONSTRAINT backtest_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;` (or `RESTRICT`) inside V017. Compare V011 / V013 / V016 which correctly declare `ON DELETE CASCADE` at column creation.

### BE-L2-002: Live WS shared DB connection never rolls back — first DB error permanently poisons the socket
- Severity hint: **Important**
- Area: ws / reliability
- Evidence: `backend/api/ws/live.py:100` opens one `db_conn = connect()` per socket. `_latest_bars` (line 44-66) runs SELECTs via `_candles.get_latest_candles_batch(conn, …)` inside `asyncio.to_thread`. On failure, `poll_once` (line 102-135) catches `Exception`, sends a `LIVE_POLL_FAILED` frame — but **never** calls `conn.rollback()`. The conn is closed only in `finally` at socket close (line 211).
- Impact: psycopg opens an implicit transaction on the first statement. Any DB error (transient network blip, invalid symbol/tf raising `NotFoundError`, TimescaleDB restart, etc.) leaves the connection in `InFailedSqlTransaction`. Every subsequent poll re-uses the same conn and fails with `current transaction is aborted, commands ignored until end of transaction block` — the client sees an infinite stream of `LIVE_POLL_FAILED` errors and never recovers until it manually disconnects. G-009 batched 1m queries, but did not add rollback/reconnect logic.
- Repro/notes: `_latest_bars` should either use autocommit (`db_conn.autocommit = True` right after connect), or the `except` block in `poll_once` must `db_conn.rollback()` (and ideally reconnect on repeated failure). Also `require_active_symbol` inside `get_latest_candles_batch` (candle_service.py:167) raises `NotFoundError` — client subscribes to an unknown symbol → first exception → session dead.

### BE-L2-003: OpenAPI spec still contradicts the enforced auth matrix (major)
- Severity hint: **Important**
- Area: api-contract / docs
- Evidence (all in `backend/docs/openapi.yaml`):
  - Lines 13-16 (top-level description): lists `scan`, `backtest`, `replay`, `live WS`, `POST /users`, `GET /users/{id}`, `/auth/*`, `/ai/*` as **public**. Actual code requires JWT on scan, backtest, replay (create/get/delete), live WS, AI (`/ai/translate`, `/ai/clarify`, `/ai/explain`), and same-user JWT on `GET /users/{id}`.
  - Lines 634-703 (`POST /backtest`, `GET /backtest/{run_id}`, `GET /backtest/{run_id}/trades`): no `security:` block. Actual code — `backtest.py:38,55,66` — all `Depends(get_current_user)`.
  - Lines 705-729 (`POST /scan`) and (missing) `GET /scan/{scan_id}`: no security, and the `GET` route (implemented in `scan.py:42`) isn't documented at all. This directly re-opens the old BE-023 gap for the read side.
  - Lines 731-808 (`POST /ai/translate`, `/ai/clarify`, `/ai/explain`): no security. Tag description still says "Phase 10; public".
  - Lines 810-859 (`POST/GET/DELETE /replay/sessions`): no security, no 401.
  - Lines 441-490 (`GET/PATCH/DELETE /users/{user_id}`): no `security:`, no 401/403. Actual code — `users.py:61-92` — requires JWT + `require_same_user`.
  - Lines 411-439 (`GET /users`): documented as returning 200 `UserResponse` list. Actual code — `users.py:43-58` — returns HTTP 410 with `GONE`. No `410` response documented at all.
- Impact: Consumers (SDK generators, `openapi-typescript`, integration tests) will code to the wrong contract — e.g. skip `Authorization` on scan/backtest/replay, treat 401/403 as bugs, expect a users list. FE/BE drift and mistrust of the spec.

### BE-L2-004: Replay WS close-code documentation in OpenAPI still says superseded = 4401 (contradicts BE code and G3 "aligned")
- Severity hint: **Important**
- Area: ws / api-contract
- Evidence:
  - `backend/docs/openapi.yaml:875-876`: “Unknown `session_id` closes the socket with application code **4404** (`REPLAY_NOT_FOUND`) before any replay events. A superseded concurrent connection closes with **4401**.”
  - `backend/api/ws/replay.py:32-34`: `WS_UNAUTHORIZED = 4401`, `WS_SUPERSEDED = 4402`, `WS_REPLAY_NOT_FOUND = 4404`.
  - `F2_BACKEND_REMEDIATION.md:44-50` explicitly states 4401=UNAUTHORIZED, 4402=SUPERSEDED, and warns FE not to map 4401 to superseded.
  - G3 spot-check line: "OpenAPI has no `/auth/claim`" — that part is fine — but G3 did **not** re-verify replay close codes in openapi.yaml. The stale text is still there.
- Impact: FE / third-party clients coded from the spec will treat 4401 as "opened in another tab" (amber, keep auth) instead of "unauthorized" (clear auth) and vice-versa. Directly re-opens G-002 for downstream consumers.

### BE-L2-005: Live WS OpenAPI still labelled "Public in v1" but code enforces JWT
- Severity hint: **Important**
- Area: ws / api-contract
- Evidence: `backend/docs/openapi.yaml:912` — “Public in v1 (same trust model as historical candles).” vs. `backend/api/ws/live.py:77-85` which closes with 4401 when `?token=`/Authorization is missing or invalid.
- Impact: Same as BE-L2-003 — clients coded from spec fail to connect; browsers assume ws://.../ws/live is anonymous.

### BE-L2-006: `ReplaySessionCreate.user_id` still on the wire and its docstring says "logging only until auth (Phase 11)"
- Severity hint: **Important** (misleading / attribution forgery vector re-appears if any future path trusts the field)
- Area: api / schemas
- Evidence:
  - `backend/api/schemas/replay.py:30-40` — `user_id: UUID | None = None` with docstring "Optional; logging only until auth (Phase 11)."
  - `backend/api/routers/replay.py:31-39` — service ignores `body.user_id` and uses `current.id`.
- Impact: The old BE-005 pattern (client-supplied `user_id`) is closed operationally but the schema still lies to clients (they see a `user_id` field they think they can set). If a future code path — a background job, a CLI, or a test — instantiates `ReplaySessionCreate` and forwards `body.user_id`, ownership can be forged. Prefer explicit removal + OpenAPI cleanup. Same field also leaks in the OpenAPI schema.

### BE-L2-007: `get_optional_user` fails hard on stale/invalid tokens, breaking public `/chart-data`
- Severity hint: **Important**
- Area: auth / api
- Evidence:
  - `backend/api/deps.py:79-92` — `get_optional_user` calls `_user_from_token(conn, token)` unconditionally when a token is present.
  - `backend/api/deps.py:95-109` — `_user_from_token` raises `UnauthorizedError` on bad signature / expiry / unknown subject.
  - `backend/api/routers/chart_data.py:33` — uses `get_optional_user` for a route documented as "public candle windows".
- Impact: A logged-out browser that still has an expired token in `localStorage` (or a token signed with a different `JWT_SECRET` during rotation) receives 401 on **every** chart request — even when `runId` is not present and the intent is fully public. Contradicts `chart_data.py:37-39` docstring ("public candle windows") and BE-comment in the service (line 127-128). Should treat invalid tokens on optional paths as "no user" and only enforce auth when `runId` is set.

### BE-L2-008: `register` catches every `UniqueViolation`, not just email — watchlist unique-index conflict returns "Unable to register with the provided email"
- Severity hint: **Important**
- Area: auth / data-integrity
- Evidence:
  - `backend/api/services/auth_service.py:94-99` catches `psycopg.errors.UniqueViolation` and re-raises `ValidationError("REGISTRATION_FAILED", "Unable to register with the provided email")`.
  - `backend/api/services/auth_service.py:70-79` provisions a default watchlist with `is_default=True` in the same tx.
  - `backend/data/migrations/sql/V012__watchlist_default_and_email.sql:17-19` adds `uq_watchlists_one_default_per_user` — a partial unique index on `(user_id) WHERE is_default`.
  - `UserService.create` at `user_service.py:52-71` has the same shape (same over-catch).
- Impact: If provisioning ever creates two default watchlists in flight (concurrent test, retry, background migration), the resulting `UniqueViolation` bubbles up as "email conflict" and misleads ops/users. Same for any future unique index (email lower, symbol dedup). Fix: narrow to email — inspect `exc.diag.constraint_name` or catch email-specific unique index by name — or roll back before checking. Rolling back and re-raising as a distinct code would be safer.

### BE-L2-009: Rate-limit + WS-slot state is process-local and unbounded (per-worker, memory leak)
- Severity hint: **Important**
- Area: reliability / security
- Evidence:
  - `backend/api/deps.py:26-31` — `_ai_hits: dict[UUID, deque[float]]` and `_ws_counts: dict[UUID, int]` are module-level.
  - `rate_limit_ai` (line 123-137) never cleans up empty deques or removes deleted users' entries.
  - `acquire_ws_slot` / `release_ws_slot` grow `_ws_counts` on demand and never shrink map size.
  - Multi-worker deployment (uvicorn `--workers N`) multiplies effective quotas by N.
- Impact:
  1. AI-cost DoS: with 4 workers and `AI_MAX_RPM=30`, a single user can burst 120 upstream LLM calls/min.
  2. WS cap `WS_MAX_CONNECTIONS_PER_USER=5` becomes 5×N in practice.
  3. Long-running process leaks memory (one entry per every user id ever seen).
  BE-004 mitigation is therefore only partial; ops guidance / Redis-backed limiter is warranted.

### BE-L2-010: No rate limit on `POST /auth/register` or `POST /users` — anonymous account spam / email squatting
- Severity hint: **Important**
- Area: security / reliability
- Evidence:
  - `backend/api/routers/auth.py:24-30` and `backend/api/routers/users.py:23-34` — neither depends on any limiter.
  - `.env.example:29-33` documents compute caps only for scan/backtest/AI/WS.
- Impact: An unauthenticated attacker can spam accounts (each triggers `bcrypt.gensalt()` + a full INSERT + default-watchlist provisioning) both to DoS the API/DB and to squat email addresses. The V012 lower-email unique index makes squatting cheap and permanent (until manual cleanup). Combine with BE-L2-009 and this is the easiest resource-exhaustion vector against the API.

### BE-L2-011: Login timing side-channel enables email enumeration
- Severity hint: **Important**
- Area: security / auth
- Evidence:
  - `backend/api/auth.py:46-62` — `verify_password(password, None)` short-circuits to `False` immediately (no bcrypt work) when `password_hash is None` (i.e. email not found).
  - `backend/api/services/auth_service.py:105-110` — login path calls `get_by_email` then `verify_password`.
- Impact: An attacker measuring response times can enumerate valid emails: unknown-email ≈ single DB roundtrip; known-email ≈ DB + one bcrypt round (`~50-200 ms`). This is the same class of leak BE-024 documented for `claim`; login itself is still leaky. Fix: verify against a fixed dummy bcrypt hash when the user row is missing, so both paths take the same wall-clock time.

### BE-L2-012: WS slot leak on `websocket.accept()` failure
- Severity hint: **Minor**
- Area: ws / reliability
- Evidence:
  - `backend/api/ws/replay.py:120-135` — `acquire_ws_slot` runs, then `_active_connections.get`, then `await websocket.accept()` — all *outside* the try/finally that starts at line 137. `release_ws_slot` is only in that outer `finally` (line 249-252).
  - `backend/api/ws/live.py:87-93` has the same shape (acquire before `accept()`, release only inside inner `finally`).
- Impact: If accept() fails (client already disconnected, TLS abort mid-handshake, etc.), the slot count for the user increments and never decrements. Over time a user's cap fills with ghosts and locks them out. Move `acquire_ws_slot` under the outer try or reset the counter in an explicit `except` before returning.

### BE-L2-013: `_active_connections` dict in replay WS is unlocked
- Severity hint: **Minor**
- Area: ws / concurrency
- Evidence: `backend/api/ws/replay.py:36` — plain `dict`. Concurrent connect attempts for the same `session_id` from two clients read/write without a lock. The "supersede prior" step (line 126-132) can send a close to the wrong socket if a third client races between the `get` and the assignment on line 135.
- Impact: Race can leak orphan entries and confuse the "same session opened in another tab" UX. Not exploitable, but non-deterministic — add an `asyncio.Lock()` or an atomic `dict.pop` around the swap.

### BE-L2-014: Scan `persist=true` silently swallows every persistence error (no logging, `persisted=False`)
- Severity hint: **Minor**
- Area: reliability / observability
- Evidence: `backend/api/services/scan_service.py:151-174` — `try: self._scans.insert(...) ... except Exception: scan_id = None; persisted = False`. No `logger.exception`, no metric, no error surfacing.
- Impact: A DB outage, permission drift, or a bad constraint (see BE-L2-015) silently reports `"persisted": false` with no diagnostic. Ops sees "everything is fine" while nothing is being written. Add at least `logger.exception` and, ideally, propagate a soft error code in the response.

### BE-L2-015: `data_gaps` unique index only prevents *exact* duplicates — overlapping distinct ranges still race
- Severity hint: **Minor**
- Area: data-integrity
- Evidence:
  - `backend/data/migrations/sql/V014__data_gaps_constraints.sql:44-46` — `UNIQUE (symbol, timeframe, start_ts, end_ts) WHERE status = 'open'`.
  - `backend/data/gaps.py:191-204` — `reconcile_gaps` skips insert when a detected range overlaps any existing open gap, but this check is application-level and not transactionally serialized across sync workers.
- Impact: Two concurrent `run_sync` workers detecting non-identical but overlapping ranges (e.g. one covers `10:00-10:05`, the other `10:03-10:10`) both pass the app-level overlap check and both insert. The unique index does not catch it. The V014 startup dedupe helps on first apply but does nothing at steady state. Consider an `EXCLUDE USING gist (symbol WITH =, timeframe WITH =, tstzrange(start_ts, end_ts, '[]') WITH &&) WHERE (status = 'open')` constraint (btree_gist / btree_gist plus `daterange`).

### BE-L2-016: V017 destructive delete of `backtest_runs` on migration — under-documented data loss
- Severity hint: **Minor**
- Area: migrations / data-integrity
- Evidence: `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql:3` — `DELETE FROM app.backtest_runs WHERE user_id IS NULL`. Because V008 was `ON DELETE SET NULL`, any backtests attributable to already-deleted users become orphaned NULL owners and are silently discarded on migrate.
- Impact: Silent data destruction during deploy. G2-002/G3 note V017 exists but no doc calls out that historical backtest analytics may vanish. Would be safer to `UPDATE ... SET user_id = <system_user>` or archive before deleting.

### BE-L2-017: `SESSION_NOT_FOUND` mapped to 404, hides other-user access from ownership check
- Severity hint: **Minor**
- Area: security / api-contract
- Evidence: `backend/api/services/ai_service.py:29-35` — always returns `NotFoundError` (404) for `SESSION_NOT_FOUND`. `ai/sessions.py` (`PostgresClarificationSessionStore.get`) filters on `user_id` and returns `None` for cross-user access.
- Impact: The behaviour (404 for both "no session" and "wrong owner") is actually the *intended* anti-enumeration pattern and mirrors G-004's `NotFoundError` choice. But the error `message` embeds the caller-provided `session_id` (`f"Unknown or expired session: {session_id}"`) — that echo is harmless but unhelpful. Not a bug — flagged for consistency with the ownership-404 convention.

### BE-L2-018: `_map_error` for `SESSION_NOT_FOUND` returns 404 while `POST /ai/clarify` OpenAPI already declares 404 — the response envelope carries the raw session id back
- Severity hint: **Minor** (grouped)
- Area: api-contract
- Evidence: `docs/openapi.yaml:783-786` — `POST /ai/clarify` documents `404` NotFound. Consistent with implementation. Just note the echo above.

### BE-L2-019: `POST /users` still exists but duplicates `/auth/register` (no JWT returned, no rate limit, misleading OpenAPI)
- Severity hint: **Minor**
- Area: api-contract
- Evidence:
  - `backend/api/routers/users.py:23-34` — creates a user + default watchlist, returns `UserResponse` (no JWT).
  - OpenAPI `/api/v1/users` `POST` (line 391-410) describes the same flow but does not point clients at `/auth/register` (which is the actual FE bootstrap path).
- Impact: Confusing surface with two anonymous account-creation routes. Consider deprecating `POST /users` or making it JWT-protected + admin-only. The FE bootstrap in this repo already uses `/auth/register`; keeping `POST /users` open costs a spam surface for no benefit.

### BE-L2-020: Migrator advisory lock is session-level but not scoped by database — cross-DB deploys on the same cluster contend
- Severity hint: **Minor**
- Area: migrations / reliability
- Evidence: `backend/data/migrations/migrator.py:26,107` — uses `pg_advisory_lock(0xC8B7_AC75_E57E_0001)`; single global key.
- Impact: If the same Postgres instance hosts multiple `backtester` databases (blue/green, multi-tenant staging), simultaneous migrations serialize across DBs that don't need to serialize. Not incorrect, but the intent was "one migration per DB" — consider `pg_advisory_lock(hashtext(current_database()))`.

---

## Clean areas (brief)

- **Fail-closed env / JWT / CORS**: `settings.app_env()`, `jwt_secret()`, `cors_origins()` are coherent; `test_settings.py` covers dev/prod/placeholder/empty-CORS matrix. `main.py:52` calls `validate_security_settings()` before serving.
- **Replay WS distinct close codes**: `WS_UNAUTHORIZED=4401`, `WS_SUPERSEDED=4402`, `WS_REPLAY_NOT_FOUND=4404` at BE. Only the OpenAPI doc is stale (BE-L2-004); the BE-side handler is correct.
- **Ownership 404 on scan/backtest**: `scan_service.get`, `backtest_service.get_run`, `backtest_service.get_chart_overlays`, and `chart_data_service.get_chart_data` all return `RUN_NOT_FOUND` / `SCAN_NOT_FOUND` for cross-user access.
- **Replay session ownership**: `V011` NOT NULL + `require_session` filter; `V016`/`V017` bring parity for scan and backtest.
- **BE-001 scan commit**: `scan_repository.insert` commits; scan router now attributes to `current.id`.
- **Auth `claim` removal**: Confirmed removed from router, service, and OpenAPI.
- **Register anti-enumeration**: `REGISTRATION_FAILED` in place; login uses generic `INVALID_CREDENTIALS`.
- **CHECK constraints (V015) on `replay_sessions.state`, `backtest_runs.status`, `scan_runs.status`**: correctly enforce state literals; matches app-level values.
- **`GET /users` enumeration**: correctly gated behind 410 GONE in code (only the OpenAPI is stale).
- **Live WS 1m batching (G-009)**: `_latest_bars` groups by timeframe and uses `ANY(%s)` for 1m; verified.
- **Derived TF incompleteness gate (BE-009)**: `SELECT_DERIVED_CANDLES_BY_RANGE` `HAVING COUNT(*) >= expected AND bucket_ts + interval <= max_ts + '1 minute'` is present.
- **Migrator advisory lock**: applied per session before pending scan (BE-011 addressed).

## Remaining issue count

**20** (1 critical, 10 important, 9 minor)

### Issue IDs and one-line titles (for parent)

- BE-L2-001 — V008 FK `ON DELETE SET NULL` conflicts with V017 `NOT NULL` (user delete broken)
- BE-L2-002 — Live WS shared DB connection never rolls back → session-long poison after first error
- BE-L2-003 — OpenAPI omits `security: bearerAuth` on scan/backtest/replay/AI/users; `GET /users` 410 undocumented
- BE-L2-004 — OpenAPI replay-WS doc still says superseded = 4401 (BE uses 4402)
- BE-L2-005 — OpenAPI live WS still labelled "Public in v1"; code requires JWT
- BE-L2-006 — `ReplaySessionCreate.user_id` still in schema/wire but ignored (misleading + attribution risk if reused)
- BE-L2-007 — `get_optional_user` 401s on stale tokens for public chart-data
- BE-L2-008 — `register` catches every `UniqueViolation` (watchlist partial-unique too) as "email conflict"
- BE-L2-009 — In-process AI RPM + WS slot maps are per-worker and unbounded (multi-worker bypass + leak)
- BE-L2-010 — No rate limit on `POST /auth/register` / `POST /users`
- BE-L2-011 — Login timing side-channel (bcrypt only for existing users) enables email enumeration
- BE-L2-012 — WS slot leak if `websocket.accept()` throws (acquire outside try/finally)
- BE-L2-013 — `_active_connections` dict unlocked (concurrent-connect race)
- BE-L2-014 — Scan persist swallows every exception silently (no log/metric)
- BE-L2-015 — `data_gaps` unique index only exact match; overlapping distinct ranges still race
- BE-L2-016 — V017 destructive `DELETE FROM backtest_runs WHERE user_id IS NULL` is under-documented
- BE-L2-017 — AI `SESSION_NOT_FOUND` 404 embeds caller-provided session id in message (informational)
- BE-L2-018 — OpenAPI clarify 404 documented but message echoes session id (grouped with -017)
- BE-L2-019 — `POST /users` still open (duplicates `/auth/register`, no JWT return, no rate limit)
- BE-L2-020 — Migrator advisory lock key not scoped by database name (cross-DB contention)
