# Agent D (Loop 2) — Backend Solutions

**Date:** 2026-08-11
**Inputs:** `LOOP2_A_BACKEND_ISSUES.md`, `LOOP2_C_SEVERITY_DEPENDENCY.md`
**Scope:** BE-L2-001 … BE-L2-020, plus `BE-for-FE-L2-003` (WS-ticket / subprotocol endpoint required by FE-L2-003).

For every issue below, at least two implementable solutions are described and exactly one is marked **Recommended**. Solutions are chosen to (a) match the existing codebase style (single-file migrations under `backend/data/migrations/sql/V*.sql`, service objects, `psycopg` connection lifecycle, `ApiError` envelope), (b) stay migration-safe, and (c) keep the FE/BE contract truthful so Agents E/F can regenerate typed clients from a single trustworthy `openapi.yaml`.

---

### BE-L2-001: V008 `ON DELETE SET NULL` conflicts with V017 `NOT NULL` — user delete will fail
Severity: Critical | Effort: S | Rank: 1

#### Solution 1: New V018 migration that swaps the FK action to `ON DELETE CASCADE`
- Approach: Add `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql` that runs `ALTER TABLE app.backtest_runs DROP CONSTRAINT backtest_runs_user_id_fkey, ADD CONSTRAINT backtest_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES app.users(id) ON DELETE CASCADE;`. Matches `V011`, `V013`, `V016` which already use `ON DELETE CASCADE` for `user_id`.
- Pros/Cons: Pros — parity with scan/replay/AI/watchlist FK actions, `DELETE /users/{id}` becomes a single transactional cascade, no data preserved for deleted users (GDPR-friendly). Cons — deleting a user permanently loses their historical backtest runs (already true in intent by V017).
- Files/migrations likely touched:
  - New file: `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql`
  - Test: `backend/tests/data/migrations/test_backtest_runs_cascade.py` (regression: create user + backtest + delete user asserts 0 backtest rows and 204 from `DELETE /users/{id}`).

#### Solution 2: `ON DELETE RESTRICT` + explicit archive step
- Approach: New V018 rewrites the FK to `ON DELETE RESTRICT` and adds a service-layer teardown in `UserService.delete_user` that first `UPDATE app.backtest_runs SET user_id = <deleted_users_sentinel>` (or moves rows to `app.backtest_runs_archive`) before issuing the `DELETE app.users`.
- Pros/Cons: Pros — preserves analytics history under a sentinel/archive owner; explicit ops trail. Cons — new sentinel row + policy for it, more code, harder to reason about; contradicts the ownership-only 404 pattern G-004 established (a sentinel row is enumerable by anyone who guesses the id). Also requires either a new migration for the sentinel/archive table or a documented ops runbook.
- Files/migrations likely touched:
  - New file: `backend/data/migrations/sql/V018__backtest_runs_fk_restrict_plus_archive.sql`
  - New file: `backend/data/migrations/sql/V019__backtest_runs_archive.sql` (optional archive table).
  - `backend/api/services/user_service.py:delete_user` (pre-delete reassignment).
  - `backend/api/routers/users.py` (still 204, but now depends on service performing the reassignment).

#### Recommended: Solution 1
Justification: Matches the ownership-cascade pattern already used by `V011`/`V013`/`V016`; smallest surgical change; V017's intent was already "orphan backtests should not survive their owner".
Implementation notes for Agent F:
- Create `backend/data/migrations/sql/V018__backtest_runs_fk_cascade.sql` with:
  ```sql
  ALTER TABLE app.backtest_runs
      DROP CONSTRAINT backtest_runs_user_id_fkey;

  ALTER TABLE app.backtest_runs
      ADD CONSTRAINT backtest_runs_user_id_fkey
      FOREIGN KEY (user_id)
      REFERENCES app.users (id)
      ON DELETE CASCADE;
  ```
- Do **not** wrap in `IF EXISTS` — the constraint is created by V008 and unconditionally present; failing loud is desired here.
- Add integration test `backend/tests/api/test_users_delete.py::test_delete_user_cascades_backtest_runs`: register, run a small `POST /backtest`, `DELETE /users/{id}` returns 204, subsequent `SELECT COUNT(*) FROM app.backtest_runs WHERE user_id = <id>` returns 0.
- Land this together with BE-L2-016 (see below) — they share the migration cutover.

---

### BE-L2-002: Live WS shared DB connection never rolls back — session-long poison after first error
Severity: Important | Effort: S | Rank: 3

#### Solution 1: Set `db_conn.autocommit = True` on connect
- Approach: In `backend/api/ws/live.py:100`, immediately after `db_conn = connect()`, set `db_conn.autocommit = True`. All `_latest_bars` SELECTs run outside an implicit transaction, so a `NotFoundError` from `get_latest_candles_batch` or a transient error never leaves the connection in `InFailedSqlTransaction`.
- Pros/Cons: Pros — one-line fix; matches the read-only nature of the live poller; no state to reason about. Cons — no atomic multi-statement reads (irrelevant here — every poll is a single `SELECT`); autocommit changes have subtle interactions with cursors that hold snapshots, but the poller only executes one query per subscription pass.
- Files/migrations likely touched:
  - `backend/api/ws/live.py` (~line 100).
  - Test: `backend/tests/api/ws/test_live_ws.py` (inject a `_candles.get_latest_candles_batch` raising `NotFoundError`; assert socket still delivers a `candle` on the next poll after the client re-`subscribe`s a valid symbol).

#### Solution 2: `conn.rollback()` in the `poll_once` exception paths + reconnect on repeated failure
- Approach: Wrap `poll_once`'s `except ValidationError` and `except Exception` in `_safely_reset_conn(db_conn)` which calls `db_conn.rollback()` inside a `try`. Track consecutive failures; after N (e.g. 3), close and re-open the connection.
- Pros/Cons: Pros — keeps transactional semantics if future code writes to DB inside a poll (unlikely here). Cons — more moving parts, must also handle the case where the socket already sent the error frame; reconnect logic risks leaking file descriptors if not carefully finally-scoped.
- Files/migrations likely touched:
  - `backend/api/ws/live.py` (`poll_once` and a new helper).

#### Recommended: Solution 1
Justification: The live WS DB connection is strictly read-only and per-poll; autocommit is the least-code, most robust way to guarantee no `InFailedSqlTransaction` poison.
Implementation notes for Agent F:
- In `backend/api/ws/live.py`, change:
  ```python
  db_conn = connect()
  ```
  to:
  ```python
  db_conn = connect()
  db_conn.autocommit = True
  ```
- Add a regression test in `backend/tests/api/ws/test_live_ws.py`:
  1. Monkeypatch `_candles.get_latest_candles_batch` to raise on the first call (e.g. `NotFoundError("SYMBOL_NOT_FOUND", ...)`), then return a real bar on subsequent calls.
  2. Assert the client receives one `error`/`LIVE_POLL_FAILED` frame, then a `candle` frame on the next poll cycle without disconnect/reconnect.
- Also add a guard in `_latest_bars` (defense-in-depth): catch `NotFoundError` for unknown symbols and record `results[key] = None` instead of propagating — this stops one bad client subscription from tearing down the whole poll. Track the invalid key in the returned dict so `poll_once` can emit a single `INVALID_SYMBOL` error frame per key rather than repeatedly on every poll.

---

### BE-L2-003: OpenAPI omits `security: bearerAuth` on scan/backtest/replay/AI/users; `GET /users` 410 undocumented
Severity: Important | Effort: M | Rank: 8

#### Solution 1: Hand-edit `openapi.yaml` in one PR ("OpenAPI truthing")
- Approach: In `backend/docs/openapi.yaml`, add `security: - bearerAuth: []` blocks (and `401`/`403`/`404` response refs) to every operation that requires JWT: `POST /scan`, `GET /scan/{scan_id}`, `POST /backtest`, `GET /backtest/{run_id}`, `GET /backtest/{run_id}/trades`, `POST /ai/translate`, `POST /ai/clarify`, `POST /ai/explain`, `POST /replay/sessions`, `GET /replay/sessions/{session_id}`, `DELETE /replay/sessions/{session_id}`, `GET /users/{user_id}`, `PATCH /users/{user_id}`, `DELETE /users/{user_id}`. Add the missing `GET /api/v1/scan/{scan_id}` path. Replace `GET /api/v1/users` with a `410 Gone` response. Rewrite the top-of-file description (lines 12-16) and the two `ai` tag descriptions (lines 56-59) so "public" only refers to health/symbols/candles/chart-data/indicators/meta/`/auth/*`.
- Pros/Cons: Pros — a single reviewable PR gets the schema-of-record correct; unblocks all typed-client work (FE-L2-005/006). Cons — laborious; risk of drift if someone touches the spec without following the same pattern. Mitigate by adding a contract test that iterates over app.routes and asserts `security` presence for every route that depends on `get_current_user`.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml` (many operations plus tags and description).
  - New test: `backend/tests/api/test_openapi_contract.py::test_all_authed_routes_have_bearer_security` — walks FastAPI's `app.routes`, checks each `dependant.dependencies` for `get_current_user`/`get_optional_user`/`require_same_user`, and asserts the matching path in the YAML has `security: [{bearerAuth: []}]`.

#### Solution 2: Serve FastAPI's auto-generated OpenAPI and delete the hand-written YAML
- Approach: Delete `backend/docs/openapi.yaml`, expose FastAPI's `/openapi.json` (already generated from routers + `Depends(get_current_user)`), and add a `security_schemes` block using FastAPI's `HTTPBearer(auto_error=False)`.
- Pros/Cons: Pros — spec cannot drift because it is derived from the code. Cons — big change: current YAML has curated descriptions/tag copy, `x-websocket` blocks (not part of OpenAPI at all), and precise example values that would need to be reproduced as `openapi_extra` decorators; a lot of existing tests probably reference the YAML. Fails the "avoid massive refactor when surgical fix works" rule.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml` (deleted).
  - `backend/api/main.py` (openapi customization).
  - Every router that needs `responses={401: {...}, 403: {...}}` decorators.

#### Recommended: Solution 1
Justification: Preserves the hand-curated tag copy, `x-websocket` sections, and description-driven examples while directly fixing the truth gap; the contract test blocks regression cheaply.
Implementation notes for Agent F:
- Group all edits into a single "OpenAPI truthing" PR (per Agent C's note) that also lands BE-L2-004, BE-L2-005, BE-L2-006 to avoid regenerating typed clients four times.
- For each protected operation add:
  ```yaml
  security:
    - bearerAuth: []
  responses:
    "401":
      description: Missing or invalid JWT
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"
    "403":
      description: Not the resource owner
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"
  ```
  (Add `403` only where `require_same_user`/ownership is enforced.)
- Add `/api/v1/scan/{scan_id}` mirroring `getBacktest` (uses `ScanRunResponse`, 404 example `SCAN_NOT_FOUND`).
- Replace `GET /api/v1/users` responses:
  ```yaml
  responses:
    "410":
      description: Enumeration removed; use GET /auth/me
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"
  ```
  (Also drop the misleading `200` array response.)
- Rewrite `info.description` lines 12-16 to move `scan`, `backtest`, `replay`, `live WS`, `POST /users`, `GET /users/{id}`, `/ai/*` from "public" to "Protected". Keep `health`, `symbols`, `candles`, `chart-data`, `indicators`, `meta`, `/auth/register`, `/auth/login` as public.
- Add `backend/tests/api/test_openapi_contract.py` per above; use `TestClient(app).get("/openapi.json")` only if `/openapi.json` is served, otherwise `yaml.safe_load(open("backend/docs/openapi.yaml"))`.
- Also drop the duplicated `ai` tag block (lines 56-59 have two `ai` entries).

---

### BE-L2-004: OpenAPI replay-WS doc still says superseded = 4401 (BE uses 4402)
Severity: Important | Effort: S | Rank: 7

#### Solution 1: Rewrite the `x-websocket.replay.description` close-code table
- Approach: Update `backend/docs/openapi.yaml:875-876` and the surrounding paragraph to match the constants in `backend/api/ws/replay.py:32-34`: `4401 UNAUTHORIZED`, `4402 SUPERSEDED`, `4404 REPLAY_NOT_FOUND`, `4429 WS_LIMIT`. Add a small YAML table of `{code, reason, meaning, expected FE action}`.
- Pros/Cons: Pros — doc becomes authoritative; FE authors coding from spec (FE-L2-007) get the right map first try. Cons — none; pure doc.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml` (~line 862-905).

#### Solution 2: Introduce module-level constants exported as OpenAPI examples via `openapi_extra`
- Approach: Move the close-code table into a Python enum in `backend/api/ws/replay.py`, publish via a FastAPI startup hook that injects it into `app.openapi_schema["x-websocket"]["replay"]["closeCodes"]`. Same for `live`.
- Pros/Cons: Pros — single source of truth (constants). Cons — bigger footprint for a doc-only bug; conflicts with Solution 1 above (`openapi.yaml` is hand-authored, not generated by FastAPI in this project).
- Files/migrations likely touched:
  - `backend/api/ws/replay.py`, `backend/api/ws/live.py`, `backend/api/main.py`, `backend/docs/openapi.yaml`.

#### Recommended: Solution 1
Justification: The YAML is hand-authored; a targeted doc rewrite is safe and lands inside the same "OpenAPI truthing" PR (BE-L2-003).
Implementation notes for Agent F:
- Rewrite the replay `description` in `backend/docs/openapi.yaml`:
  ```yaml
  x-websocket:
    replay:
      path: /ws/replay/{session_id}
      description: |
        ...
        Close codes (application layer):
          4401 UNAUTHORIZED       — missing or invalid JWT (FE: clear session, show AuthGate)
          4402 SUPERSEDED         — same session opened in another tab (FE: amber banner, keep auth)
          4404 REPLAY_NOT_FOUND   — session unknown or not owned by JWT subject
          4429 WS_LIMIT           — per-user WS concurrency cap reached (FE: distinct toast)
  ```
- Also patch the "live" block (see BE-L2-005 below) with the same 4401/4429 table.
- Add a small regression test `backend/tests/docs/test_openapi_close_codes.py` that loads the YAML and asserts the four numbers `4401 4402 4404 4429` appear in `x-websocket.replay.description`.

---

### BE-L2-005: OpenAPI live WS still labelled "Public in v1"; code requires JWT
Severity: Important | Effort: S | Rank: 6

#### Solution 1: Rewrite `x-websocket.live` prose in `openapi.yaml`
- Approach: Change `backend/docs/openapi.yaml:912` to state that `/ws/live` requires a JWT via `?token=<jwt>` **or** `Authorization: Bearer` header (mirroring `backend/api/deps.py:159-166` and `backend/api/ws/live.py:77-85`). Document close codes 4401 (`UNAUTHORIZED`) and 4429 (`WS_LIMIT`), and update the `LiveWsCandleEvent` example to confirm the `bar` field name.
- Pros/Cons: Pros — makes FE-L2-001 and FE-L2-002 straightforward to fix; small YAML edit. Cons — none.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml` (`x-websocket.live` block).

#### Solution 2: Add a machine-checkable "protected" attribute to `x-websocket` blocks + contract test
- Approach: Introduce a custom YAML field `x-websocket.live.security: [{bearerAuth: []}]` (and same for replay), and a test that scans `backend/api/ws/*.py` for `resolve_ws_token` usage to assert the flag is set.
- Pros/Cons: Pros — regression-proof. Cons — invents a project-local convention that isn't standard OpenAPI; Solution 1 already produces a truthful spec.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml`.
  - `backend/tests/docs/test_openapi_ws_security.py`.

#### Recommended: Solution 1
Justification: Land as part of the same "OpenAPI truthing" PR; minimal, standard-YAML change.
Implementation notes for Agent F:
- Replace the `live` description in `backend/docs/openapi.yaml`:
  ```yaml
  live:
    path: /ws/live
    description: |
      Live candle tail (Phase 11). Requires JWT via `?token=<jwt>` or
      `Authorization: Bearer` header (BE-004). Polls TimescaleDB for the latest
      **closed** candle per subscription and pushes a `candle` event when the
      bar `time` changes.

      Close codes:
        4401 UNAUTHORIZED — missing or invalid JWT
        4429 WS_LIMIT     — per-user WS concurrency cap reached

      Poll interval: `LIVE_WS_POLL_INTERVAL_MS` (default 2000ms).
  ```
- In `components.schemas.LiveWsCandleEvent`, confirm `required: [type, symbol, timeframe, bar]` and add an `example` showing `bar: { time, open, high, low, close, volume }` so FE-L2-001 (field-name mismatch) can be caught by contract tests.

---

### BE-L2-006: `ReplaySessionCreate.user_id` still on the wire (misleading + attribution risk if reused)
Severity: Important | Effort: S | Rank: 9

#### Solution 1: Delete the `user_id` field from `ReplaySessionCreate`
- Approach: Remove the field from `backend/api/schemas/replay.py:30-40` and remove its component in `backend/docs/openapi.yaml:1595-1599`. Router already ignores `body.user_id` and uses `current.id` (`backend/api/routers/replay.py:39`), so no runtime change is required for well-behaved clients. Regenerate FE types.
- Pros/Cons: Pros — schema truth; no future accidental trust of client-supplied id; matches the ownership-only pattern for backtest and scan. Cons — a client that was posting `user_id` (harmlessly) now gets `422 Unprocessable Entity` from Pydantic. Impact assessment: no known caller sends it (FE doesn't), and BE was already ignoring it, so this is effectively a no-op for real traffic.
- Files/migrations likely touched:
  - `backend/api/schemas/replay.py:30-40`.
  - `backend/docs/openapi.yaml:1595-1599`.
  - `backend/tests/api/test_replay_router.py` (add regression: `POST` with `user_id` yields 422; `POST` without succeeds and session is owned by JWT subject).

#### Solution 2: Keep the field but declare it `deprecated` and reject non-null values
- Approach: Mark `user_id` as `deprecated: true` in OpenAPI, keep the pydantic field, and add a validator that raises `ValueError` when `user_id is not None`.
- Pros/Cons: Pros — smooth deprecation window if any downstream client still sends the field. Cons — keeps a footgun in the schema; still leaves the misleading field visible to code readers and OpenAPI consumers.
- Files/migrations likely touched:
  - `backend/api/schemas/replay.py`.
  - `backend/docs/openapi.yaml`.

#### Recommended: Solution 1
Justification: There are no known callers, the router already ignores it, and hard removal closes both the schema-of-truth gap and the latent attribution-forgery vector in one line.
Implementation notes for Agent F:
- In `backend/api/schemas/replay.py`, drop the `user_id: UUID | None = None` field and rewrite the class docstring accordingly.
- In `backend/docs/openapi.yaml`, delete the `user_id` block inside `ReplaySessionCreate`.
- Add test `backend/tests/api/test_replay_router.py::test_create_replay_session_rejects_user_id`: POST body `{"symbol": "BTC/USDT", "timeframe": "1h", "start": ..., "user_id": "<uuid>"}` → 422 (`extra_forbidden` — set `model_config = ConfigDict(extra="forbid")` on `ReplaySessionCreate` if not already, else assert Pydantic's default `extra="ignore"` still ignores; either way the OpenAPI schema no longer advertises the field).
- Land in the same "OpenAPI truthing" PR as BE-L2-003/004/005.

---

### BE-L2-007: `get_optional_user` 401s on stale tokens for public chart-data
Severity: Important | Effort: S | Rank: 2

#### Solution 1: Swallow `UnauthorizedError` in `get_optional_user`; only enforce auth when `runId` present in the caller
- Approach: In `backend/api/deps.py:79-92`, wrap the `_user_from_token` call in `try/except UnauthorizedError: return None`. Then, in `backend/api/routers/chart_data.py`, add an explicit `if run_id is not None and current is None: raise UnauthorizedError()` check so overlays remain fail-closed.
- Pros/Cons: Pros — fixes the logged-out-with-stale-token UX (`localStorage` residue after JWT rotation, expired tokens) without opening ownership overlays to anonymous callers. Matches the docstring intent ("public candle windows, auth required when `runId` is set"). Cons — introduces a per-route explicit check; keep it in the router, not the dep, so intent is visible.
- Files/migrations likely touched:
  - `backend/api/deps.py:79-92` (`get_optional_user`).
  - `backend/api/routers/chart_data.py` (add `runId`-gated auth check).
  - `backend/tests/api/test_chart_data_router.py` (three cases: no token → 200; expired token, no runId → 200; expired token + runId → 401).

#### Solution 2: Keep `get_optional_user` strict; add a new `get_public_or_current_user` dep for chart-data
- Approach: Leave `get_optional_user` behaviour intact (raises on bad token). Create a second dep `get_public_or_current_user` used only by `chart_data.py` that catches `UnauthorizedError` and returns `None`, and rely on the service layer to raise `UnauthorizedError` when it encounters `run_id` with no user.
- Pros/Cons: Pros — no behaviour change for other callers of `get_optional_user` (audit: `Grep get_optional_user` shows only chart-data uses it today, so this benefit is theoretical). Cons — two nearly-identical deps invite confusion; more code for the same effect.
- Files/migrations likely touched:
  - `backend/api/deps.py` (new dep).
  - `backend/api/routers/chart_data.py` (swap dep).

#### Recommended: Solution 1
Justification: Only chart-data uses `get_optional_user` today; changing its behaviour to be truly optional is the minimal fix and matches the documented intent, while an explicit `runId → auth required` check keeps overlays fail-closed and visible in the router.
Implementation notes for Agent F:
- Modify `backend/api/deps.py`:
  ```python
  def get_optional_user(...):
      token = _extract_bearer_token(credentials, authorization)
      if not token:
          return None
      try:
          return _user_from_token(conn, token)
      except UnauthorizedError:
          return None
  ```
- In `backend/api/routers/chart_data.py:get_chart_data`, add before the service call:
  ```python
  if run_id is not None and current is None:
      raise UnauthorizedError()
  ```
  (Import from `api.auth`.)
- Update tests:
  - `test_chart_data_router.py::test_chart_data_public_ignores_expired_token` — Authorization header with a hand-crafted expired JWT, no `runId`, expect 200 with candles.
  - `test_chart_data_router.py::test_chart_data_run_id_requires_valid_token` — Same expired token + `runId`, expect 401 `UNAUTHORIZED`.

---

### BE-L2-008: `register` catches every `UniqueViolation` (watchlist partial-unique too) as "email conflict"
Severity: Minor (per Agent C, downgraded from Important) | Effort: S | Rank: 16

#### Solution 1: Narrow the `UniqueViolation` catch by `exc.diag.constraint_name`
- Approach: In `backend/api/services/auth_service.py:register` and `backend/api/services/user_service.py:create`, inspect `exc.diag.constraint_name`. If it is `uq_users_email_lower` (or historically `users_email_key`), raise `REGISTRATION_FAILED`. Otherwise `conn.rollback()` and re-raise as a distinct `ValidationError("PROVISIONING_CONFLICT", ...)` with `logger.exception` for ops.
- Pros/Cons: Pros — accurate error surface, no misleading "email exists" for watchlist / future unique indices; small diff. Cons — relies on `psycopg`'s diag; test needs to simulate a non-email `UniqueViolation` (e.g. two default watchlists via crafted `WatchlistRepository`).
- Files/migrations likely touched:
  - `backend/api/services/auth_service.py:94-99`.
  - `backend/api/services/user_service.py:52-71`.
  - `backend/tests/api/services/test_auth_service.py` (add case: force `uq_watchlists_one_default_per_user` violation → expect `PROVISIONING_CONFLICT`, not `REGISTRATION_FAILED`).

#### Solution 2: Provision the default watchlist in a *separate* transaction after user commit
- Approach: Split `register` into two transactions: first commit the user row (email violation → `REGISTRATION_FAILED`), then in a second transaction insert the default watchlist (any violation → log + return the auth token anyway; watchlist can be reprovisioned lazily on first `GET /users/{id}/watchlists`).
- Pros/Cons: Pros — cleanly attributes each error class. Cons — breaks the BE-012 all-or-nothing invariant (partial user without a default watchlist); needs a compensating self-heal in the watchlist read path; more moving parts.
- Files/migrations likely touched:
  - `backend/api/services/auth_service.py`, `backend/api/services/user_service.py`.
  - `backend/api/services/watchlist_service.py` (lazy provisioning).

#### Recommended: Solution 1
Justification: Preserves the BE-012 transactional invariant; single-file surgical change; the diag-based narrow catch is exactly the pattern Agent A suggested.
Implementation notes for Agent F:
- In `backend/api/services/auth_service.py`:
  ```python
  except psycopg.errors.UniqueViolation as exc:
      conn.rollback()
      constraint = getattr(exc.diag, "constraint_name", "") or ""
      if constraint in {"uq_users_email_lower", "users_email_key"}:
          raise ValidationError(
              "REGISTRATION_FAILED", "Unable to register with the provided email"
          ) from exc
      logger.exception("Unexpected unique violation during register: %s", constraint)
      raise ValidationError(
          "PROVISIONING_CONFLICT",
          "Registration failed due to a provisioning conflict",
      ) from exc
  ```
- Mirror the same change in `backend/api/services/user_service.py::create` (and, defensively, `update_user` for `uq_users_email_lower`).
- Import a module-level `logger = logging.getLogger(__name__)`.
- Test with a monkeypatched `WatchlistRepository.create` that raises `psycopg.errors.UniqueViolation` with `diag.constraint_name = "uq_watchlists_one_default_per_user"` — expect `PROVISIONING_CONFLICT`, not `REGISTRATION_FAILED`.

---

### BE-L2-009: In-process AI RPM + WS slot maps are per-worker and unbounded (multi-worker bypass + leak)
Severity: Important | Effort: L | Rank: 13

#### Solution 1: Redis-backed sliding window + WS counter behind a `RateLimiter` interface
- Approach: Introduce `backend/api/rate_limiter.py` with a `RateLimiter` protocol and two implementations: `InProcessRateLimiter` (current behaviour, still default when `REDIS_URL` unset — good for dev/tests) and `RedisRateLimiter` (uses `redis-py`'s `INCR` + `EXPIRE` for the RPM window, and `INCR`/`DECR` on `ws:conn:{user_id}` for slots, guarded by TTL to auto-heal stale counters). `deps.rate_limit_ai` / `acquire_ws_slot` / `release_ws_slot` become thin façades that call the process-wide limiter, chosen at import time by settings. Also add periodic cleanup of empty deques in `InProcessRateLimiter` (defensive for memory leak in the single-worker case).
- Pros/Cons: Pros — accurate global limits under multi-worker; unblocks BE-L2-010 (same limiter); tests can use the in-process fallback; dev experience unchanged when `REDIS_URL` not set. Cons — adds a `redis` dependency and a new required env var for prod; requires a `fakeredis` (or `docker compose` redis) fixture for integration testing.
- Files/migrations likely touched:
  - New: `backend/api/rate_limiter.py`.
  - `backend/api/deps.py:26-31, 123-137, 140-149, 152-156` (replace module-level maps + funcs with limiter façade).
  - `backend/api/settings.py` (`redis_url()`; default `None`).
  - `backend/pyproject.toml` (add `redis>=5.0`).
  - `.env.example` (`REDIS_URL=redis://localhost:6379/0`).
  - New test: `backend/tests/api/test_rate_limiter.py` (both implementations).
  - Integration: `backend/tests/api/test_deps_rate_limit.py` with a `fakeredis.FakeRedis` fixture.

#### Solution 2: Keep in-process, but bound the map and document `--workers 1`
- Approach: Wrap `_ai_hits`/`_ws_counts` in an `LRU` (e.g. `cachetools.TTLCache(maxsize=10_000, ttl=3600)`), and add a startup check that logs a loud warning if `WEB_CONCURRENCY > 1` (or `--workers > 1`), plus an ops-guidance section in `.env.example` telling operators to run a single worker until Redis is added.
- Pros/Cons: Pros — no new infrastructure; bounds memory. Cons — does not solve the correctness problem (limits still per-worker); pushes the multi-worker constraint onto ops with no runtime enforcement.
- Files/migrations likely touched:
  - `backend/api/deps.py`, `backend/api/main.py` (startup warning), `.env.example`.

#### Recommended: Solution 1
Justification: Only a shared-store limiter actually delivers the promised cap under multi-worker, which is exactly the reliability gap A flagged; keeping the in-process fallback preserves the existing test/dev ergonomics.
Implementation notes for Agent F:
- Sketch of `backend/api/rate_limiter.py`:
  ```python
  class RateLimiter(Protocol):
      def check_ai_rpm(self, user_id: UUID, limit: int) -> None: ...
      def acquire_ws(self, user_id: UUID, max_conn: int) -> None: ...
      def release_ws(self, user_id: UUID) -> None: ...
  ```
  In-process implementation retains current deque logic but wraps `_ai_hits`/`_ws_counts` in `cachetools.TTLCache(maxsize=10_000, ttl=3600)`.
  Redis implementation uses `INCR ai:rpm:{user}:{minute_bucket}` with `EXPIRE 90` for RPM; `INCR ws:conn:{user}` gated with `WATCH`/`MULTI` on `check-and-decrement` to reject when count would exceed the cap. On `release`, `DECR` and clamp at 0. For heal: set `EXPIRE 3600` on `ws:conn:{user}` after any INCR so orphaned counters (dead worker) auto-expire.
- Factory `get_rate_limiter()` reads `settings.redis_url()`; when `None` returns `InProcessRateLimiter` singleton; otherwise `RedisRateLimiter(redis.Redis.from_url(...))`.
- Replace bodies of `rate_limit_ai`, `acquire_ws_slot`, `release_ws_slot` in `backend/api/deps.py` to delegate to `get_rate_limiter()`.
- Update `.env.example` with `REDIS_URL=` and a note explaining fallback semantics + `WEB_CONCURRENCY` interaction.
- Add a test suite parametrised over both implementations (skip Redis one when `fakeredis` import fails).

---

### BE-L2-010: No rate limit on `POST /auth/register` / `POST /users`
Severity: Important | Effort: M | Rank: 12

#### Solution 1: Per-IP + per-email account-creation limiter dep
- Approach: Add a new dep `rate_limit_anonymous(request: Request, body: AuthRegisterRequest | UserCreate)` in `backend/api/deps.py` that uses the same `RateLimiter` façade introduced in BE-L2-009 (keys: `register:ip:{client_ip}`, `register:email:{lower(email)}`; limits: e.g. 5 req/min per IP, 3 req/hour per email). Wire into `POST /auth/register` and `POST /users`. Client IP comes from `Request.client.host` with a settings-gated `X-Forwarded-For` trust chain (`TRUST_PROXY_HEADERS=true` → take leftmost after honoring `TRUSTED_PROXY_CIDRS`).
- Pros/Cons: Pros — fail-closed, works for both anonymous account routes, integrates with the Redis limiter for correctness under multi-worker, per-email prevents email squatting even when IP rotates. Cons — needs care with proxy headers; wrong trust chain either bypasses the limit (dev NAT) or over-blocks (shared corporate IP).
- Files/migrations likely touched:
  - `backend/api/deps.py` (`rate_limit_anonymous`, `_client_ip(request)`).
  - `backend/api/routers/auth.py:24-30`, `backend/api/routers/users.py:23-34`.
  - `backend/api/settings.py` (`auth_register_ip_rpm()`, `auth_register_email_rph()`, `trust_proxy_headers()`).
  - `backend/tests/api/test_auth_router.py::test_register_rate_limited_by_ip` and `test_register_rate_limited_by_email`.

#### Solution 2: Front-door protection via reverse proxy (nginx/Cloudflare) + captcha on Nth attempt
- Approach: Delegate rate limiting to the reverse proxy (nginx `limit_req_zone`), and add a `POST /auth/register` challenge (e.g. hCaptcha) enforced by the router when a header from the proxy indicates "high-risk".
- Pros/Cons: Pros — offloads bot mitigation to a mature layer. Cons — assumes an ops-managed proxy exists in every deployment; adds a hard external dependency; captcha increases friction and requires FE UX.
- Files/migrations likely touched:
  - Ops config (nginx). `backend/api/routers/auth.py` for captcha token verification.

#### Recommended: Solution 1
Justification: In-app fail-closed limiter mirrors the pattern used for AI/WS, works in every deploy without an external proxy, and reuses the BE-L2-009 façade so both are one PR family.
Implementation notes for Agent F:
- Land after (or with) BE-L2-009's `RateLimiter` façade.
- Add to `backend/api/deps.py`:
  ```python
  def _client_ip(request: Request) -> str:
      if settings.trust_proxy_headers():
          xff = request.headers.get("x-forwarded-for", "")
          if xff:
              return xff.split(",")[0].strip()
      return request.client.host if request.client else "unknown"

  def rate_limit_anonymous_register(
      request: Request,
      body: AuthRegisterRequest,
  ) -> None:
      limiter = get_rate_limiter()
      limiter.check_named("register:ip", _client_ip(request),
                         limit=settings.auth_register_ip_rpm(), window_sec=60)
      limiter.check_named("register:email", body.email.strip().lower(),
                         limit=settings.auth_register_email_rph(), window_sec=3600)
  ```
- Wire into `router.post("/register", ..., dependencies=[Depends(rate_limit_anonymous_register)])` in `backend/api/routers/auth.py`.
- Add a matching (leaner) dep for `POST /users` that keys on `body.email` similarly.
- Defaults in `.env.example`: `AUTH_REGISTER_IP_RPM=5`, `AUTH_REGISTER_EMAIL_RPH=3`, `TRUST_PROXY_HEADERS=false`.
- On limit exceeded raise `ValidationError("RATE_LIMITED", ...)` (already maps to 4xx via `ApiError`); consider 429 status by adding a `RateLimitError(ApiError, status_code=429)` in `api/exceptions.py`.

---

### BE-L2-011: Login timing side-channel (bcrypt only for existing users) enables email enumeration
Severity: Minor (per Agent C, downgraded) | Effort: S | Rank: 17

#### Solution 1: Precomputed dummy bcrypt hash + always-verify on missing user
- Approach: Add a module-level constant `_DUMMY_BCRYPT_HASH` in `backend/api/auth.py` (a real bcrypt hash of an unreachable value, computed at import time with the current cost factor). Change `AuthService.login` to always call `bcrypt.checkpw` — either against `user.password_hash` or against `_DUMMY_BCRYPT_HASH` when the user is missing — and only then decide the outcome. Also fix `verify_password` to run a dummy compare when `password_hash is None` so timing is symmetric even if callers rely on it.
- Pros/Cons: Pros — normalises response time to a single bcrypt round on both branches; no schema change; kept-in-place for future auth flows. Cons — small extra CPU (one bcrypt per failed-unknown-email login) — negligible with BE-L2-010 rate limits.
- Files/migrations likely touched:
  - `backend/api/auth.py` (`_DUMMY_BCRYPT_HASH`, tweak `verify_password`).
  - `backend/api/services/auth_service.py:105-110` (call the always-verify helper).
  - `backend/tests/api/test_auth_login_timing.py` (parametric test that measures average wall-clock deltas across N=20 attempts with known-vs-unknown emails; use a small tolerance because bcrypt cost varies).

#### Solution 2: Enforce constant-time via `asyncio.sleep` padding to a fixed budget
- Approach: Wrap `login` in a decorator that measures elapsed time and `await asyncio.sleep(budget - elapsed)` before returning.
- Pros/Cons: Pros — simple. Cons — brittle to CPU load; must be pessimistically padded; hides actual latency; still leaks under high-precision timing.
- Files/migrations likely touched:
  - `backend/api/services/auth_service.py`.

#### Recommended: Solution 1
Justification: The industry-standard dummy-hash pattern is straightforward, robust to load, and gives a real (not simulated) constant-cost branch.
Implementation notes for Agent F:
- In `backend/api/auth.py`:
  ```python
  _DUMMY_BCRYPT_HASH = bcrypt.hashpw(b"unused-timing-normaliser", bcrypt.gensalt()).decode("utf-8")

  def verify_password(password: str, password_hash: str | None) -> bool:
      target = password_hash or _DUMMY_BCRYPT_HASH
      try:
          matched = bcrypt.checkpw(password.encode("utf-8"), target.encode("utf-8"))
      except (ValueError, TypeError):
          matched = False
      return matched and password_hash is not None
  ```
- No change needed in `AuthService.login` — `verify_password` now always does the same bcrypt work.
- Regression test: 20 known + 20 unknown login attempts; assert `abs(mean_known - mean_unknown) < 20ms` (bcrypt round-trip should dominate).

---

### BE-L2-012: WS slot leak if `websocket.accept()` throws (acquire outside try/finally)
Severity: Minor | Effort: S | Rank: 20

#### Solution 1: Move `acquire_ws_slot` inside the outer `try/finally`
- Approach: In both `backend/api/ws/replay.py:120-135` and `backend/api/ws/live.py:87-93`, restructure so that the acquire happens inside a `try:` block whose `finally:` unconditionally calls `release_ws_slot(user.id)`. If `websocket.accept()` raises, the finally still fires and decrements.
- Pros/Cons: Pros — surgical; matches idiomatic Python resource management; no new abstractions. Cons — a `try/finally` around a large body is easy to break by later refactors — mitigate by wrapping the whole "after acquire" section in a nested try.
- Files/migrations likely touched:
  - `backend/api/ws/replay.py` (~lines 120-252).
  - `backend/api/ws/live.py` (~lines 87-214).
  - `backend/tests/api/ws/test_ws_slot_leak.py` (monkeypatch `websocket.accept` to raise; assert count decrements to 0).

#### Solution 2: Context manager `WsSlot(user_id)` used by both routers
- Approach: Introduce a `@contextlib.contextmanager` `ws_slot(user_id)` in `deps.py` that acquires on enter and releases on exit. Both routers `with ws_slot(user.id):` around the entire post-auth body.
- Pros/Cons: Pros — impossible to forget the release. Cons — WebSocket handlers are `async` and mix acquisition with `await websocket.close(...)` calls that happen *before* accept; a context manager forces a particular structure and can complicate the "reject with 4429 without accepting" branch.
- Files/migrations likely touched:
  - `backend/api/deps.py`, both `ws/*.py`.

#### Recommended: Solution 1
Justification: Direct fix; keeps the existing structure and error-close paths intact; least risk.
Implementation notes for Agent F:
- In `backend/api/ws/replay.py`, restructure to:
  ```python
  try:
      acquire_ws_slot(user.id)
  except ValidationError as exc:
      await websocket.close(code=4429, reason=exc.code)
      return
  try:
      prior = _active_connections.get(session_id)
      if prior is not None: ...
      await websocket.accept()
      _active_connections[session_id] = websocket
      # ... existing body ...
  finally:
      if _active_connections.get(session_id) is websocket:
          del _active_connections[session_id]
      release_ws_slot(user.id)
      # existing checkpoint block
  ```
- Same pattern for `backend/api/ws/live.py` (finally must still `db_conn.close()` and `release_ws_slot`).
- Test with a `WebSocket` monkeypatch whose `accept()` raises `RuntimeError`, then assert `get_rate_limiter().ws_count(user.id) == 0`.

---

### BE-L2-013: `_active_connections` dict unlocked (concurrent-connect race)
Severity: Minor | Effort: S | Rank: 21

#### Solution 1: Guard `_active_connections` swap with an `asyncio.Lock`
- Approach: Introduce a module-level `_active_lock = asyncio.Lock()` in `backend/api/ws/replay.py`. Wrap the read-then-supersede-then-store sequence (`prior = _active_connections.get(...); ...; _active_connections[session_id] = websocket`) under `async with _active_lock:`. Delete path (in `finally`) also acquires the lock briefly.
- Pros/Cons: Pros — deterministic supersede; matches asyncio idioms. Cons — very short lock, held across an `await prior.close(...)`; if `prior.close()` hangs, other connect attempts for the same session are queued (acceptable — they were already superseded).
- Files/migrations likely touched:
  - `backend/api/ws/replay.py:36` (new lock), lines 126-135 and 249-251 (wrap).

#### Solution 2: Atomic swap via `dict.pop`/`setdefault`
- Approach: Use `_active_connections.pop(session_id, None)` before the supersede step and `_active_connections.setdefault(session_id, websocket)`; still not atomic across an `await`, so the race actually persists — this is only cosmetically safer. Rejected as insufficient.
- Pros/Cons: Pros — no explicit lock. Cons — awaits interleave and re-open the race; doesn't fix the described bug.
- Files/migrations likely touched:
  - `backend/api/ws/replay.py`.

#### Recommended: Solution 1
Justification: The only correct answer in an `asyncio` cooperative scheduler is an explicit `asyncio.Lock` around the check-then-set critical section.
Implementation notes for Agent F:
- Add at module top of `backend/api/ws/replay.py`:
  ```python
  _active_lock = asyncio.Lock()
  ```
  (import `asyncio`.)
- Wrap:
  ```python
  async with _active_lock:
      prior = _active_connections.get(session_id)
      _active_connections[session_id] = websocket
  if prior is not None:
      try:
          await _send_json(prior, _error_event("SUPERSEDED", ...))
          await prior.close(code=WS_SUPERSEDED, reason="SUPERSEDED")
      except Exception:
          pass
  await websocket.accept()
  ```
  (Note: promote the register-in-map inside the lock, but do the notify/close of `prior` outside — the map is authoritative already.)
- In `finally`, guard the delete: `async with _active_lock: _active_connections.pop(session_id, None) if _active_connections.get(session_id) is websocket else None` — or use a helper `_swap_out(session_id, websocket)`.
- Add a race test that spawns two `TestClient` connects concurrently against the same `session_id` and asserts (a) the earlier socket received a `SUPERSEDED` close with code 4402 and (b) the map has exactly one entry when both finish.

---

### BE-L2-014: Scan persist swallows every exception silently (no log/metric)
Severity: Minor | Effort: S | Rank: 24

#### Solution 1: `logger.exception` + `persist_error_code` in response envelope
- Approach: In `backend/api/services/scan_service.py:171`, log via `logger.exception("scan_persist_failed", extra={"scan_id": candidate_id})`. Extend `ScanRunResponse` with an optional `persist_error: str | None = None` field, and set it to `"PERSIST_FAILED"` when the try/except triggers so FE / ops can distinguish "persist disabled by request" from "persist attempted and failed".
- Pros/Cons: Pros — observable in logs immediately; distinguishable in API response; no behavioural change for consumers ignoring the new field. Cons — new optional response field must be added to OpenAPI (`ScanRunResponse`).
- Files/migrations likely touched:
  - `backend/api/services/scan_service.py:151-174` (logging + optional error code).
  - `backend/api/schemas/scan.py` (`persist_error: str | None`).
  - `backend/docs/openapi.yaml` (extend `ScanRunResponse`).
  - Test: `backend/tests/api/services/test_scan_service.py` (`insert` raises → `persisted=False`, `persist_error="PERSIST_FAILED"`, log captured).

#### Solution 2: Re-raise persist failures as `ApiError` (fail-loud)
- Approach: Remove the swallow entirely; a `POST /scan?persist=true` failure returns 500 with `SCAN_PERSIST_FAILED` and the compute result is lost.
- Pros/Cons: Pros — impossible to miss. Cons — punishes the client for an infrastructure issue; loses compute work; contradicts BE-001's "honest persistence flag" design.
- Files/migrations likely touched:
  - `backend/api/services/scan_service.py`.

#### Recommended: Solution 1
Justification: Preserves the honest-flag semantics while giving ops the observability the swallow currently denies.
Implementation notes for Agent F:
- In `backend/api/services/scan_service.py`:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ...
  except Exception:
      logger.exception("Scan persist failed for candidate_id=%s", candidate_id)
      scan_id = None
      persisted = False
      persist_error = "PERSIST_FAILED"
  ```
- Extend `ScanRunResponse` (`backend/api/schemas/scan.py`) with `persist_error: str | None = None`.
- Extend OpenAPI `ScanRunResponse` accordingly (part of BE-L2-003 PR is fine).
- Optional: emit a Prometheus counter if the project has one; audit shows no metrics library is present, so log-only is sufficient for now.

---

### BE-L2-015: `data_gaps` unique index only exact match; overlapping distinct ranges still race
Severity: Minor | Effort: M | Rank: 28

#### Solution 1: `EXCLUDE USING gist` constraint with `btree_gist` extension
- Approach: New migration `V019__data_gaps_no_overlap.sql` that:
  1. `CREATE EXTENSION IF NOT EXISTS btree_gist;`
  2. Pre-clean any already-overlapping open rows (reuse V014's dedupe DELETE pattern).
  3. `ALTER TABLE data_gaps ADD CONSTRAINT data_gaps_no_open_overlap EXCLUDE USING gist (symbol WITH =, timeframe WITH =, tstzrange(to_timestamp(start_ts), to_timestamp(end_ts), '[]') WITH &&) WHERE (status = 'open');` (adapt to `int8range` since `start_ts`/`end_ts` are `BIGINT` in Timescale — `int8range(start_ts, end_ts, '[]') WITH &&`).
- Pros/Cons: Pros — database-level correctness; two concurrent writers get one `ExclusionViolation` deterministically. Cons — requires `btree_gist` extension permissions on the target Postgres role; slightly heavier index than the current unique btree; migration writes SQL that may need superuser for extension create (Timescale Cloud already has it).
- Files/migrations likely touched:
  - New: `backend/data/migrations/sql/V019__data_gaps_no_overlap.sql`.
  - `backend/data/gaps.py:191-204` (drop the app-level `_ranges_overlap` skip since DB now enforces; catch `psycopg.errors.ExclusionViolation` in `reconcile_gaps` → treat as "already recorded, skip").
  - Test: `backend/tests/data/test_gaps.py` (two concurrent inserts of overlapping-but-non-identical ranges).

#### Solution 2: Advisory lock per `(symbol, timeframe)` around `reconcile_gaps`
- Approach: Wrap the app-level overlap check + insert in `SELECT pg_advisory_xact_lock(hashtext(symbol || '|' || timeframe));` inside the same transaction. Two writers serialise on the same pair; overlap detection remains app-side but is now transactionally correct.
- Pros/Cons: Pros — no extension requirement; no schema change. Cons — application-level ordering means a buggy caller that bypasses `reconcile_gaps` still races; not enforced at rest.
- Files/migrations likely touched:
  - `backend/data/gaps.py:reconcile_gaps`.

#### Recommended: Solution 1
Justification: The DB-level `EXCLUDE` constraint is the only fix that survives future callers who might insert directly; matches how V014 sets its per-key uniqueness at the schema layer.
Implementation notes for Agent F:
- Confirm the deploy target supports `CREATE EXTENSION btree_gist` (Timescale docs: yes).
- New migration:
  ```sql
  CREATE EXTENSION IF NOT EXISTS btree_gist;

  -- Pre-clean overlapping open rows: keep earliest id per (symbol,timeframe) overlap chain.
  DELETE FROM data_gaps a
  USING data_gaps b
  WHERE a.status = 'open'
    AND b.status = 'open'
    AND a.symbol = b.symbol
    AND a.timeframe = b.timeframe
    AND a.id > b.id
    AND a.start_ts <= b.end_ts
    AND b.start_ts <= a.end_ts;

  ALTER TABLE data_gaps
      ADD CONSTRAINT data_gaps_no_open_overlap
      EXCLUDE USING gist (
          symbol WITH =,
          timeframe WITH =,
          int8range(start_ts, end_ts, '[]') WITH &&
      ) WHERE (status = 'open');
  ```
- Update `backend/data/gaps.py::reconcile_gaps` to catch `psycopg.errors.ExclusionViolation` on `create_gap` and treat as a no-op (log at DEBUG). Remove the app-level `_ranges_overlap` pre-check if desired, or keep as an optimisation.
- Regression test: two `run_sync` invocations racing on the same `(symbol, timeframe)` with overlapping detected ranges; assert exactly one row inserted.

---

### BE-L2-016: V017 destructive `DELETE FROM backtest_runs WHERE user_id IS NULL` under-documented
Severity: Minor | Effort: S | Rank: 27

#### Solution 1: Pre-flight archive step + release-notes callout in the V018 pair
- Approach: The V018 migration for BE-L2-001 already refactors the FK; in the same migration, insert orphan rows into `app.backtest_runs_archive` before V017's DELETE ran (or, if V017 has already applied in dev/prod, emit a warning row in `schema_migrations_notes`). Add a `docs/runbooks/V017_backfill.md` explaining the destructive semantics. Because V017 has already been shipped in some environments, most of the "safe pre-flight" is now retrospective — provide an `ops/scripts/recover_orphan_backtests.sql` script that queries WAL/backup for orphan history if needed.
- Pros/Cons: Pros — future migrations follow a "archive first, delete last" template; recoverable audit trail. Cons — for environments where V017 already ran and orphans are gone, the archive is retrospective (best-effort).
- Files/migrations likely touched:
  - New: `backend/data/migrations/sql/V018_5__backtest_runs_archive.sql` (optional; only if we actually want the archive table). Otherwise:
  - New file: `docs/runbooks/V017_backfill.md`.
  - Amend `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql` with a leading comment block warning ops (this file is already applied — annotate for future readers, don't change semantics).

#### Solution 2: Backfill orphan rows to a synthetic system user before delete
- Approach: Create a system user `system@internal` in a migration, then `UPDATE app.backtest_runs SET user_id = <system_id> WHERE user_id IS NULL` (retroactively add this into a V018 for environments that still have such rows).
- Pros/Cons: Pros — preserves history under a queryable owner. Cons — same reservations as BE-L2-001 Solution 2 (sentinel enumerable, blurs ownership); most environments already applied V017 so no orphans remain.
- Files/migrations likely touched:
  - New: `backend/data/migrations/sql/V018__backtest_runs_system_backfill.sql`.

#### Recommended: Solution 1
Justification: V017 is already applied in most environments; the highest-value action now is documentation + a template for future destructive migrations (archive-first). Keeps BE-L2-001's cascade fix clean and small.
Implementation notes for Agent F:
- Amend `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql` header (idempotent — file re-read is a no-op) to include:
  ```sql
  -- WARNING: This migration is destructive. It deletes any backtest_runs whose
  -- user_id is NULL (pre-ownership orphans). Historical backtest analytics
  -- attributable to already-deleted users will vanish. Environments that
  -- require preservation must run ops/scripts/archive_orphan_backtests.sql
  -- BEFORE deploying this migration.
  ```
- Create `docs/runbooks/V017_backfill.md` describing pre-flight archive and post-fact recovery steps.
- Add `ops/scripts/archive_orphan_backtests.sql` template: `CREATE TABLE IF NOT EXISTS app.backtest_runs_archive AS SELECT * FROM app.backtest_runs WHERE 1=0; INSERT INTO app.backtest_runs_archive SELECT * FROM app.backtest_runs WHERE user_id IS NULL;`
- Cross-link this doc from `LOOP2_D_BACKEND_SOLUTIONS.md` for Agent F.

---

### BE-L2-017: AI `SESSION_NOT_FOUND` 404 embeds caller-provided session id in message (informational)
Severity: Minor | Effort: S | Rank: 30 (groups with BE-L2-018)

#### Solution 1: Drop the echoed session id from the error message
- Approach: In `backend/ai/translate.py:107,165`, change the raise from `AITranslateError("SESSION_NOT_FOUND", f"Unknown or expired session: {session_id}")` to `AITranslateError("SESSION_NOT_FOUND", "Unknown or expired session")`. The status code stays 404; the caller already knows the session id it sent.
- Pros/Cons: Pros — removes the caller-echo (small XSS surface if logs are rendered untrusted); consistent with ownership-404 anti-enumeration convention. Cons — a shade less helpful for debugging (server logs still record the id).
- Files/migrations likely touched:
  - `backend/ai/translate.py:107,165`.
  - `backend/tests/ai/test_translate.py` (adjust assertion strings if any).

#### Solution 2: Keep the id but move it to a structured field
- Approach: Extend `AITranslateError` with an optional `details: dict`, and pass `{"session_id": session_id}` there. Never render it into the message; only include in server logs via `logger.info`.
- Pros/Cons: Pros — preserves debug info out-of-band. Cons — over-engineered for a one-line fix; adds a new error-envelope field that would need OpenAPI documentation.
- Files/migrations likely touched:
  - `backend/ai/translate.py`, `backend/api/exceptions.py`, `backend/api/services/ai_service.py`, `backend/docs/openapi.yaml`.

#### Recommended: Solution 1
Justification: One-line fix, matches the ownership-404 convention, no schema change; group into the same PR as BE-L2-018 acknowledgement.
Implementation notes for Agent F:
- In `backend/ai/translate.py`, replace both instances of `f"Unknown or expired session: {session_id}"` (line 107) and `f"Unknown or expired session: {reuse_session_id}"` (line 165) with the literal `"Unknown or expired session"`.
- Log the id server-side: add `logger.info("Clarification session not found: %s", session_id)` above the raise.
- Update tests in `backend/tests/ai/test_translate.py` and `backend/tests/api/test_ai_router.py` to check for the new message (or preferably assert on `error.code == "SESSION_NOT_FOUND"` and drop the substring check).

---

### BE-L2-018: OpenAPI clarify 404 already documented — echo is the only concern (grouped)
Severity: Minor | Effort: S | Rank: 31 (blocked-by BE-L2-017)

#### Solution 1: No spec change — inherit BE-L2-017's message tightening
- Approach: BE-L2-017 removes the echoed id; OpenAPI's 404 example (`REPLAY_NOT_FOUND` shown in the `NotFound` response) already carries a generic message. Optionally, add an `ai_session` example under `components.responses.NotFound.content.application/json.examples` with `code: SESSION_NOT_FOUND, message: "Unknown or expired session"`.
- Pros/Cons: Pros — no behavioural change beyond -017; keeps the fix atomic. Cons — none.
- Files/migrations likely touched:
  - `backend/docs/openapi.yaml` (optional NotFound example addition).

#### Solution 2: Deprecate 404 for `POST /ai/clarify` in favour of 410 or a distinct code
- Approach: Change `SESSION_NOT_FOUND` to `SESSION_EXPIRED` and return `410 Gone` to signal "was valid, is no longer valid".
- Pros/Cons: Pros — semantically closer to "expired". Cons — changes the contract, breaks any existing FE mapping; contradicts the ownership-404 convention.
- Files/migrations likely touched:
  - `backend/api/services/ai_service.py`, `backend/api/exceptions.py`, `backend/docs/openapi.yaml`, FE mappers.

#### Recommended: Solution 1
Justification: The 404 mapping is deliberate (anti-enumeration parity with scan/backtest ownership-404). Only the echo needed fixing (BE-L2-017); Solution 1 preserves the contract intent.
Implementation notes for Agent F:
- Bundle with BE-L2-017's message change.
- Optionally add an example under `NotFound` response in `openapi.yaml`:
  ```yaml
  ai_session:
    value:
      error:
        code: SESSION_NOT_FOUND
        message: Unknown or expired session
  ```

---

### BE-L2-019: `POST /users` still open (duplicates `/auth/register`, no JWT return, no rate limit)
Severity: Minor | Effort: M | Rank: 25

#### Solution 1: JWT-gate `POST /users` as an admin-only route + document as deprecated
- Approach: Add a new dep `require_admin(current: UserRow = Depends(get_current_user))` in `backend/api/deps.py` (backed by a `users.is_admin BOOL DEFAULT FALSE` column added by a new migration). Attach it to `POST /users`, and mark the operation `deprecated: true` in OpenAPI with a description pointing FE clients at `POST /auth/register`. Keep behaviour otherwise so any internal admin tooling still works. Simpler variant if no admin concept is wanted yet: attach the BE-L2-010 anonymous limiter and mark `deprecated: true`.
- Pros/Cons: Pros — closes the anonymous account-creation duplicate; unifies onboarding through `/auth/register`. Cons — introduces a small admin concept (or, in the simpler variant, still leaves the route anonymous but rate-limited).
- Files/migrations likely touched:
  - `backend/api/deps.py` (`require_admin` if going the admin route).
  - `backend/data/migrations/sql/V020__users_is_admin.sql` (if admin route).
  - `backend/api/routers/users.py:23-34` (dep + deprecation description).
  - `backend/docs/openapi.yaml` (`deprecated: true`).

#### Solution 2: Delete `POST /users` and 410-gone it
- Approach: Return `410 Gone` from `POST /users`, exactly as `GET /users` does today. Any client wanting to create a user must call `/auth/register`.
- Pros/Cons: Pros — smallest attack surface; single onboarding path. Cons — breaking change for any external integration currently POSTing to `/users` (audit: FE doesn't; tests do). Requires updating test fixtures that use `POST /users` (search shows several in `backend/tests`).
- Files/migrations likely touched:
  - `backend/api/routers/users.py:23-34`.
  - `backend/docs/openapi.yaml`.
  - Migrate tests to `/auth/register`.

#### Recommended: Solution 2
Justification: The route serves no unique purpose (FE uses `/auth/register`, which already returns JWT + provisioning), keeping it live is a pure spam surface; a 410 mirroring `GET /users` is the smallest, most consistent fix and avoids introducing an admin concept before it's actually needed.
Implementation notes for Agent F:
- Rewrite `backend/api/routers/users.py:create_user` to:
  ```python
  @router.post("", status_code=status.HTTP_410_GONE)
  def create_user(_body: UserCreate) -> JSONResponse:
      return JSONResponse(
          status_code=status.HTTP_410_GONE,
          content=ErrorResponse(
              error=ErrorBody(
                  code="GONE",
                  message="POST /users is disabled; use POST /auth/register",
              )
          ).model_dump(),
      )
  ```
- Migrate any tests that call `POST /users` to `POST /auth/register` and extract `user_id` from the token envelope.
- Update `openapi.yaml` `POST /api/v1/users` to a `410` response with `ErrorResponse`.

---

### BE-L2-020: Migrator advisory lock key not scoped by database name (cross-DB contention)
Severity: Minor | Effort: S | Rank: 29

#### Solution 1: Lock key = `hashtext(current_database())`
- Approach: In `backend/data/migrations/migrator.py:26,107,140`, replace `pg_advisory_lock(MIGRATION_ADVISORY_LOCK_KEY)` with `pg_advisory_lock(hashtext(current_database()))` (two 32-bit ints if 64-bit lock is needed, e.g. `pg_advisory_lock(hashtext(current_database()), hashtext('migrations'))`). Deletes the module-level constant.
- Pros/Cons: Pros — one-liner; multiple databases on the same cluster no longer serialise. Cons — very small risk of `hashtext` collision across differently-named databases (per Postgres docs: negligible in practice).
- Files/migrations likely touched:
  - `backend/data/migrations/migrator.py:26,107,140-142`.
  - `backend/tests/data/test_migrator.py` (add regression: two migrators against distinct temporary DBs on the same cluster proceed in parallel — parametrised skip when only one DB in the test env).

#### Solution 2: Two-key lock `(hashtext(current_database()), MIGRATION_ADVISORY_LOCK_KEY)`
- Approach: Use the two-int variant of `pg_advisory_lock(int4, int4)` combining the DB name hash and the current fixed key.
- Pros/Cons: Pros — no ambiguity that this is *the* migration lock; slightly more defensible against unrelated code that also uses `pg_advisory_lock(hashtext(current_database()))`. Cons — marginally more code to keep in sync between lock/unlock.
- Files/migrations likely touched:
  - `backend/data/migrations/migrator.py`.

#### Recommended: Solution 2
Justification: Same effort as Solution 1 but avoids a theoretical collision with any other consumer that might key advisory locks by DB name — mattering as more subsystems (see BE-L2-015) may adopt advisory locking.
Implementation notes for Agent F:
- In `backend/data/migrations/migrator.py`:
  ```python
  MIGRATION_ADVISORY_LOCK_KEY = 0x0000_A1C9  # (int4); pair with hashtext(current_database())

  # In run_migrations:
  cur.execute(
      "SELECT pg_advisory_lock(hashtext(current_database()), %s)",
      (MIGRATION_ADVISORY_LOCK_KEY,),
  )
  # ... unlock:
  cur.execute(
      "SELECT pg_advisory_unlock(hashtext(current_database()), %s)",
      (MIGRATION_ADVISORY_LOCK_KEY,),
  )
  ```
- Update the module docstring/comment to record: "per-database migration lock (BE-L2-020)".
- If test infra has only one DB, add a unit test that mocks `cur.execute` and asserts the correct two-int SQL/params are used.

---

### BE-for-FE-L2-003: New WS-authentication endpoint so JWT stops living in URLs
Severity: Important | Effort: L | Rank: 14 (pairs with FE-L2-003)

Companion BE work required by FE-L2-003. The FE currently appends `?token=<jwt>` to every WS URL; the JWT leaks into DevTools/HAR/history and lives in `localStorage`. The BE must expose a way to authenticate WS handshakes without putting a long-lived bearer on the URL. Two approaches, one recommended.

#### Solution 1: `POST /api/v1/ws/tickets` short-lived one-shot ticket
- Approach: New router `backend/api/routers/ws_tickets.py` with `POST /ws/tickets` (JWT-required via `Depends(get_current_user)`) returning `{ticket: <opaque_256bit>, expires_in: 60}`. Tickets are stored in Redis (`ws:ticket:{ticket_id} -> user_id`, `EX 60`, `SETNX` + `GETDEL` on consume) — falls back to an in-process TTL cache when `REDIS_URL` unset (dev). Both `/ws/replay/{session_id}` and `/ws/live` accept `?ticket=<opaque>` **in addition to** `?token=` and `Authorization: Bearer`. `resolve_ws_token` in `backend/api/deps.py` gains a `resolve_ws_credentials(websocket, token, ticket)` helper that consumes the ticket (single-use) and returns the resolved `UserRow`. `?token=` and header bearer stay supported for backwards compatibility for one release, then removed. Emit a deprecation header (`Deprecation: true; Sunset=...`) on WS handshake when clients still use `?token=`.
- Pros/Cons: Pros — one-shot, TTL-scoped, per-user; leaks are self-healing after ≤60s; matches the same limiter façade added in BE-L2-009. Cons — requires the shared limiter store (or an in-process fallback for dev); adds a new endpoint the FE must call before every WS connect.
- Files/migrations likely touched:
  - New: `backend/api/routers/ws_tickets.py`.
  - New: `backend/api/services/ws_ticket_service.py` (Redis + in-process fallback, backed by the BE-L2-009 façade).
  - `backend/api/deps.py` (`resolve_ws_credentials`, new `user_from_ws_ticket`).
  - `backend/api/ws/replay.py` and `backend/api/ws/live.py` (accept `ticket=` query param; consume via new helper; keep `token=` as deprecated fallback).
  - `backend/api/main.py` (register new router).
  - `backend/docs/openapi.yaml` (document `POST /ws/tickets`; update `x-websocket.replay` and `x-websocket.live` handshake sections).
  - New tests: `backend/tests/api/test_ws_tickets.py` (issue ticket → consume → second consume fails; ticket expires; JWT-less request → 401), and updated WS handshake tests.

#### Solution 2: `Sec-WebSocket-Protocol` bearer smuggling
- Approach: Client passes the JWT in a `Sec-WebSocket-Protocol` header (e.g. `Sec-WebSocket-Protocol: bearer,<jwt>`). Server extracts the second value in `resolve_ws_token`, validates it, and echoes back the chosen sub-protocol (`bearer`) in the accept. Browsers do not put subprotocol values in URLs or referers.
- Pros/Cons: Pros — no new endpoint; one round-trip. Cons — still puts the *long-lived* JWT into the WS handshake headers (better than URLs but still XSS-recoverable from `localStorage`); some ops proxies strip unknown subprotocols; browser `WebSocket` API is picky about the header format; still exposes a long-lived token if the WS access log records handshake headers. Doesn't solve the "JWT lives in `localStorage`" half of FE-L2-003.
- Files/migrations likely touched:
  - `backend/api/deps.py:resolve_ws_token` (parse `Sec-WebSocket-Protocol`).
  - `backend/api/ws/replay.py`, `backend/api/ws/live.py` (accept subprotocol; echo it back in `websocket.accept(subprotocol="bearer")`).
  - `backend/docs/openapi.yaml` (document the subprotocol handshake).

#### Recommended: Solution 1
Justification: Short-lived one-shot tickets solve *both* halves of the FE-L2-003 concern (URL leakage **and** long-lived bearer exposure) and reuse the shared limiter store already introduced by BE-L2-009; the subprotocol variant only fixes the URL half.
Implementation notes for Agent F:
- Endpoint contract (draft):
  ```
  POST /api/v1/ws/tickets
    Headers: Authorization: Bearer <jwt>
    Body: {} (no payload)
    201 -> { "ticket": "<128 hex chars>", "expires_in": 60 }
    401 -> ErrorResponse (UNAUTHORIZED)
    429 -> ErrorResponse (RATE_LIMITED)   # reuse BE-L2-009/010 limiter
  ```
- Ticket format: `secrets.token_hex(32)`; store `ticket_id -> user_id` with TTL 60s; consume on WS handshake with `GETDEL` (Redis) or `pop` (in-process).
- New helper in `backend/api/deps.py`:
  ```python
  def resolve_ws_credentials(
      websocket: WebSocket,
      token: str | None,
      ticket: str | None,
  ) -> UserRow:
      if ticket:
          user_id = get_ws_ticket_service().consume(ticket)
          if user_id is None:
              raise UnauthorizedError("INVALID_TICKET", "Ticket missing or already used")
          conn = connect()
          try:
              user = _users.get_by_id(conn, user_id)
              if user is None:
                  raise UnauthorizedError("USER_NOT_FOUND", ...)
              return user
          finally:
              conn.close()
      raw = resolve_ws_token(websocket, token)
      if not raw:
          raise UnauthorizedError()
      return user_from_ws_token(raw)
  ```
- Update both WS handlers to accept `ticket: str | None = None` as a Query param and call `resolve_ws_credentials`.
- Keep `?token=` accepted for one release with a `logger.warning("ws_bearer_in_url", extra={"path": websocket.url.path})` on use; remove in the following release.
- Document in `openapi.yaml`:
  - New path `/api/v1/ws/tickets` with `security: [{bearerAuth: []}]` and the response schema above.
  - Update `x-websocket.replay` and `x-websocket.live` to say handshake auth = `?ticket=<ticket>` (preferred) or legacy `?token=<jwt>` / `Authorization: Bearer`.
- Tests:
  - `backend/tests/api/test_ws_tickets.py`: issue → consume by WS handshake → 2nd consume 401.
  - `backend/tests/api/ws/test_replay_ws.py`: replace `?token=` with `?ticket=` in test client construction; keep one legacy-token test to prove backwards compat until removal.

---

## Return-to-parent table

| Issue ID              | Recommended solution name                                                          |
|-----------------------|------------------------------------------------------------------------------------|
| BE-L2-001             | V018 migration swapping FK to `ON DELETE CASCADE`                                  |
| BE-L2-002             | `db_conn.autocommit = True` on live-WS connect                                     |
| BE-L2-003             | Hand-edit `openapi.yaml` in one "OpenAPI truthing" PR + contract test              |
| BE-L2-004             | Rewrite `x-websocket.replay.description` close-code table                          |
| BE-L2-005             | Rewrite `x-websocket.live` prose (JWT + 4401/4429)                                 |
| BE-L2-006             | Delete `user_id` field from `ReplaySessionCreate`                                  |
| BE-L2-007             | Swallow `UnauthorizedError` in `get_optional_user` + explicit `runId` auth check   |
| BE-L2-008             | Narrow `UniqueViolation` catch by `exc.diag.constraint_name`                       |
| BE-L2-009             | Redis-backed limiter behind `RateLimiter` façade (in-process fallback)             |
| BE-L2-010             | Per-IP + per-email `rate_limit_anonymous_register` dep on `/auth/register`+`/users`|
| BE-L2-011             | Precomputed dummy bcrypt hash for always-verify on missing user                    |
| BE-L2-012             | Move `acquire_ws_slot` inside the outer `try/finally` in both WS handlers          |
| BE-L2-013             | `asyncio.Lock` around `_active_connections` swap                                   |
| BE-L2-014             | `logger.exception` + `persist_error` field on `ScanRunResponse`                    |
| BE-L2-015             | `EXCLUDE USING gist` no-overlap constraint on `data_gaps` (V019 + `btree_gist`)    |
| BE-L2-016             | V017 warning header + `docs/runbooks/V017_backfill.md` + archive template          |
| BE-L2-017             | Drop echoed session id from `SESSION_NOT_FOUND` message                            |
| BE-L2-018             | Inherit -017 fix; optional NotFound example in OpenAPI                             |
| BE-L2-019             | 410 Gone on `POST /users` (mirror `GET /users`)                                    |
| BE-L2-020             | Two-int advisory lock: `(hashtext(current_database()), MIGRATION_ADVISORY_LOCK_KEY)` |
| BE-for-FE-L2-003      | `POST /api/v1/ws/tickets` short-lived one-shot ticket endpoint                     |
