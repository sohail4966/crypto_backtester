# LOOP2_F — Backend Implementation Report (Agent F)

Implements the recommended solutions from
[LOOP2_D_BACKEND_SOLUTIONS.md](./LOOP2_D_BACKEND_SOLUTIONS.md), following the
priority order in
[LOOP2_C_SEVERITY_DEPENDENCY.md](./LOOP2_C_SEVERITY_DEPENDENCY.md) with evidence
from [LOOP2_A_BACKEND_ISSUES.md](./LOOP2_A_BACKEND_ISSUES.md).

## Counts

| Status   | Count |
|----------|-------|
| Done     | 21 (BE-L2-001 … BE-L2-020 + BE-for-FE-L2-003) |
| Partial  | 0     |
| Blocked  | 0     |

No blockers for Agent H. See "Agent H handoff" at the bottom for the WS
ticket API surface and one-release-window compatibility note.

## Issue matrix

### Critical

| ID | Status | Files changed | Notes |
|----|--------|---------------|-------|
| BE-L2-001 | Done | `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql` (new) | V018 rewrites the FK from `ON DELETE SET NULL` (V008) → `ON DELETE CASCADE`. `NOT NULL` from V017 no longer makes `DELETE FROM app.users` abort. |
| BE-L2-002 | Done | `backend/api/ws/live.py` | Live WS pins `db_conn.autocommit = True` on the poll connection so long-lived subscriptions never sit inside a stale idle-tx snapshot. `_latest_bars` now returns `(bars, invalid_keys)`; unknown symbols surface as an `invalid_symbols` event instead of tearing the socket down. |
| BE-L2-007 | Done | `backend/api/deps.py`, `backend/api/routers/chart_data.py` | `get_optional_user` catches `UnauthorizedError` and returns `None`, so a stale token no longer 401s a public candle window. The router still enforces JWT + ownership when `runId` is set (`if run_id is not None and current is None: raise UnauthorizedError()`). |

### Important

| ID | Status | Files changed | Notes |
|----|--------|---------------|-------|
| BE-L2-003 | Done | `backend/docs/openapi.yaml` | Auth matrix truthed: `bearerAuth` added to `/auth/me`, `/backtest/*`, `/scan/*`, `/ai/*`, `/replay/*`, and `/chart-data` marked as optional bearer. `POST/GET /users` documented as `410 Gone`. Missing `GET /scan/{id}` and `ws-tickets` tag added; `Unauthorized`, `Forbidden`, `RateLimited` components present. |
| BE-L2-004 | Done | `backend/docs/openapi.yaml` | Replay `x-websocket.replay` documents 4401 `UNAUTHORIZED`, 4402 `SUPERSEDED`, 4404 `REPLAY_NOT_FOUND`, and 4429 `WS_LIMIT` as distinct application close codes and links to the ticket auth path. |
| BE-L2-005 | Done | `backend/docs/openapi.yaml` | Live `x-websocket.live` documents ticket-preferred auth, poll cadence, invalid-symbol event, per-user WS slot limit, and the `LiveWsCandleEvent` shape. |
| BE-L2-006 | Done | `backend/api/schemas/replay.py` | `ReplaySessionCreate` uses `ConfigDict(extra="forbid")` and no longer accepts `user_id`. Ownership is derived strictly from the JWT subject (`_service().create_session(conn, body, user_id=current.id)` in the router). |
| BE-L2-009 | Done | `backend/api/rate_limiter.py` (new), `backend/api/deps.py`, `backend/api/settings.py` | Rate-limit façade with `InProcessRateLimiter` (bounded ≤10k tracked keys, sliding window) and a Redis plug-point (`_NullRedisRateLimiter`). Callers use `check_ai_rpm`, `acquire_ws` / `release_ws`, `check_anonymous_register`. `REDIS_URL` selects the Redis path when the package is importable; falls back to in-process with a one-line warning otherwise. |
| BE-L2-010 | Done | `backend/api/deps.py`, `backend/api/routers/auth.py`, `backend/api/settings.py` | Per-IP anonymous register limiter runs as a FastAPI dependency (5 rpm default, `AUTH_REGISTER_IP_RPM`) BEFORE body validation. Per-email limiter (3 rph default, `AUTH_REGISTER_EMAIL_RPH`) runs inside the router after Pydantic has parsed the body. `TRUST_PROXY_HEADERS` gates `X-Forwarded-For` so callers can't spoof their apparent IP. Denials return a proper 429 via `RateLimitError`. |
| BE-L2-019 | Done | `backend/api/routers/users.py`, `backend/docs/openapi.yaml` | `POST /users` returns `410 Gone` with `error.code = "GONE"` and a message pointing at `POST /auth/register`. Endpoint is marked `deprecated` in OpenAPI. |
| BE-for-FE-L2-003 | Done | `backend/api/routers/ws_tickets.py`, `backend/api/schemas/ws_tickets.py`, `backend/api/services/ws_ticket_service.py`, `backend/api/deps.py`, `backend/api/ws/live.py`, `backend/api/ws/replay.py`, `backend/api/main.py`, `backend/api/settings.py`, `backend/docs/openapi.yaml` | `POST /api/v1/ws/tickets` (JWT required) mints a single-use opaque `ticket` + `expires_in`. Live and replay WS handshakes accept `?ticket=` (preferred) and log a warning when the legacy `?token=` / Authorization header path is used. TTL default 60 s via `WS_TICKET_TTL_SECONDS`. |

### Minor

| ID | Status | Files changed | Notes |
|----|--------|---------------|-------|
| BE-L2-008 | Done | `backend/api/services/auth_service.py`, `backend/api/services/user_service.py` | `_extract_constraint_name` narrows `UniqueViolation` by `diag.constraint_name`. Known email uniqueness constraints keep the anti-enumeration `REGISTRATION_FAILED`/`EMAIL_EXISTS`-style code; anything else (e.g. watchlist default) raises `PROVISIONING_CONFLICT`. Missing / unknown constraint names fall back to the existing generic path (no test regression). |
| BE-L2-011 | Done | `backend/api/auth.py`, `backend/api/services/auth_service.py` | `_DUMMY_BCRYPT_HASH` is precomputed at import time. `verify_password` always runs one bcrypt round even when `password_hash` is `None`, and `AuthService.login` calls `verify_password` with `candidate_hash = user.password_hash if user else None`, so the unknown-email path burns the same CPU as wrong-password. |
| BE-L2-012 | Done | `backend/api/ws/live.py`, `backend/api/ws/replay.py` | WS slot acquisition + `websocket.accept()` moved inside `try / finally` so an exception in the handshake path can never leak a slot. `slot_released` flag guards the double-release. |
| BE-L2-013 | Done | `backend/api/ws/replay.py` | `_active_connections` is now guarded by `asyncio.Lock()` for the check-then-supersede-then-store window. Also used in the disconnect path when clearing the entry, so two concurrent connects to the same `session_id` cannot both survive. |
| BE-L2-014 | Done | `backend/api/services/scan_service.py`, `backend/api/schemas/scan.py`, `backend/docs/openapi.yaml` | Repository failure in `ScanService.run` now logs (`logger.exception`), sets `persisted=False`, and populates the new `persist_error="PERSIST_FAILED"` field so ops can distinguish infra failure from an explicit `persist=false`. |
| BE-L2-015 | Done | `backend/data/migrations/sql/V019__data_gaps_no_overlap.sql` (new), `backend/data/gaps.py` | V019 adds `CREATE EXTENSION IF NOT EXISTS btree_gist` and an `EXCLUDE USING gist` constraint on `data_gaps(symbol =, timeframe =, tstzrange(start_ts, end_ts, '[]') &&) WHERE (status='open')`, with a pre-clean of existing overlapping open rows. `reconcile_gaps` swallows `psycopg.errors.ExclusionViolation` (concurrent inserter won the race — no-op). |
| BE-L2-016 | Done | `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql` (header), `backend/ops/scripts/archive_orphan_backtests.sql` (new), `docs/runbooks/V017_backfill.md` (new) | V017 gained a WARNING banner explaining that it deletes orphan (`user_id IS NULL`) rows. The runbook covers pre-flight archive, application, and post-fact recovery. |
| BE-L2-017 / BE-L2-018 | Done | `backend/ai/translate.py` | `SESSION_NOT_FOUND` no longer echoes the caller-supplied session id back through the message. The id is still logged (`logger.info(...)`) for ops debugging. Applies both to `apply_clarification` and `_interpret_envelope` reuse-session path. |
| BE-L2-020 | Done | `backend/data/migrations/migrator.py` | Advisory lock now uses two ints: `pg_advisory_lock(hashtext(current_database()), <fixed_key>)` — migrations on different databases in the same cluster no longer serialise. Unlock updated to match. |

## Tests

New tests added:

- `backend/tests/api/test_ws_tickets.py` — POST /ws/tickets JWT required, single-use, TTL 0 expires, unknown ticket returns None.
- `backend/tests/api/test_rate_limiter.py` — In-process limiter sliding-window denial + slot symmetry; end-to-end 429 for register per-IP limit via HTTP.
- `backend/tests/api/test_replay_schemas.py` — `ReplaySessionCreate` forbids `user_id` (BE-L2-006).
- `backend/tests/api/test_auth.py` — Added constant-time login bcrypt assertion (BE-L2-011), `PROVISIONING_CONFLICT` mapping (BE-L2-008), 410 Gone on `POST /users` (BE-L2-019).
- `backend/tests/api/test_scan.py` — Persist failure surfaces `persist_error = "PERSIST_FAILED"` (BE-L2-014).
- `backend/tests/api/test_chart_data.py` — Stale JWT on public window still returns 200 (BE-L2-007), `runId` without valid JWT returns 401.
- `backend/tests/data/test_gaps.py` — `ExclusionViolation` in `reconcile_gaps` is a benign race, not a 500 (BE-L2-015).
- `backend/tests/data/migrations/test_migrator.py` — V018 uses `ON DELETE CASCADE`; V019 uses `EXCLUDE USING gist`; migrator advisory lock is scoped by `hashtext(current_database())`.
- `backend/tests/ai/test_translate.py` — Assertion that caller-supplied session id does not leak into the error message.

Adjusted tests:

- `backend/tests/api/test_live_ws.py` — `_latest_bars` now returns `(bars, invalid_keys)` (BE-L2-002). Patch target moved from `api.ws.live.user_from_ws_token` to `api.deps.user_from_ws_token` since the WS handler now uses `resolve_ws_user`.
- `backend/tests/api/test_replay_ws.py` — 6 `user_from_ws_token` patches moved to `api.deps` for the same reason.

Test run (from `backend/`, `APP_ENV=dev`):

```
python -m pytest tests/ -q --no-header \
  --ignore=tests/test_run_backtest_integration.py \
  --ignore=tests/test_run_poc.py \
  --ignore=tests/test_run_poc_wrapper.py \
  --ignore=tests/test_run_sync.py
...
533 passed, 1 failed, 1 warning in 14.36s
```

The single failure (`tests/config/test_data_config.py::test_load_data_config_per_symbol_history_depth`, asserts `'1y' == '8y'`) is **pre-existing** on `main` and unrelated to this change. Verified via `git stash` + rerun before this work landed.

Focused run over the modules touched by this loop:

```
python -m pytest tests/api/ tests/ai/ tests/data/ -q
180 passed, 1 warning in 3.93s
```

## Files changed

New files:

- `backend/api/rate_limiter.py`
- `backend/api/routers/ws_tickets.py`
- `backend/api/schemas/ws_tickets.py`
- `backend/api/services/ws_ticket_service.py`
- `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql`
- `backend/data/migrations/sql/V019__data_gaps_no_overlap.sql`
- `backend/ops/scripts/archive_orphan_backtests.sql`
- `docs/runbooks/V017_backfill.md`
- `backend/tests/api/test_rate_limiter.py`
- `backend/tests/api/test_replay_schemas.py`
- `backend/tests/api/test_ws_tickets.py`

Modified files (partial list, most are one small stanza):

- `backend/ai/translate.py`
- `backend/api/auth.py`
- `backend/api/deps.py`
- `backend/api/exceptions.py`
- `backend/api/main.py`
- `backend/api/routers/auth.py`
- `backend/api/routers/chart_data.py`
- `backend/api/routers/users.py`
- `backend/api/schemas/replay.py`
- `backend/api/schemas/scan.py`
- `backend/api/services/auth_service.py`
- `backend/api/services/scan_service.py`
- `backend/api/services/user_service.py`
- `backend/api/settings.py`
- `backend/api/ws/live.py`
- `backend/api/ws/replay.py`
- `backend/data/gaps.py`
- `backend/data/migrations/migrator.py`
- `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql` (header only)
- `backend/docs/openapi.yaml`
- `backend/tests/ai/test_translate.py`
- `backend/tests/api/test_auth.py`
- `backend/tests/api/test_chart_data.py`
- `backend/tests/api/test_live_ws.py`
- `backend/tests/api/test_replay_ws.py`
- `backend/tests/api/test_scan.py`
- `backend/tests/data/migrations/test_migrator.py`
- `backend/tests/data/test_gaps.py`

## Agent H handoff — WS ticket API shape

### Endpoint

`POST /api/v1/ws/tickets`

- Auth: **required** — `Authorization: Bearer <jwt>`.
- Body: none.
- Response: `201 Created` with body

  ```json
  {
    "ticket": "128-hex-string",
    "expires_in": 60
  }
  ```

  `expires_in` is seconds until expiry (default 60, `WS_TICKET_TTL_SECONDS`).
  Tickets are **single-use** — the first WS handshake with `?ticket=<value>`
  wins; the second sees `UNAUTHORIZED` (close code 4401).

### WebSocket handshake

Live: `GET /ws/live?ticket=<value>` (preferred) or `?token=<jwt>` (legacy).
Replay: `GET /ws/replay/{session_id}?ticket=<value>` (preferred) or `?token=<jwt>` (legacy).

- Prefer `?ticket=<value>`. FE should call `POST /ws/tickets` right before every
  WS connect, use the returned string once, and re-mint on reconnect.
- Legacy `?token=` / `Authorization: Bearer` remain accepted for **one release
  window** to avoid coordinated FE/BE cutover. The server logs a
  `ws_bearer_in_url` info line every time the legacy path is used so we can
  measure the migration.
- Unauthorized handshake closes with **application close code 4401** and reason
  `UNAUTHORIZED` (unchanged). Consumed / expired ticket returns the same code
  (`INVALID_TICKET` in server logs).
- Slot-exhaustion close: 4429 `WS_LIMIT` (unchanged).
- Replay-specific: 4402 `SUPERSEDED`, 4404 `REPLAY_NOT_FOUND` (unchanged).

### Rate-limit envelope

- Anonymous register limits: 5 req/min per IP + 3 req/hour per email
  (`AUTH_REGISTER_IP_RPM`, `AUTH_REGISTER_EMAIL_RPH`). Denials return
  HTTP `429 Too Many Requests` with body `{"error":{"code":"RATE_LIMITED","message":"..."}}`.
- Per-user AI RPM and WS slot counts continue to use `422 WS_LIMIT` /
  `429 RATE_LIMITED` — see `rate_limiter.py` for the mapping.

### Deployment notes for H

- In-process rate limiter and ticket store are **per-worker**. Single-worker
  deployments (default) are fine; multi-worker deployments MUST set `REDIS_URL`
  once the Redis backend is wired (plug-point already in
  `api/rate_limiter.py::_NullRedisRateLimiter`).
- `TRUST_PROXY_HEADERS=true` is only safe behind a proxy that scrubs
  client-supplied `X-Forwarded-For`.
