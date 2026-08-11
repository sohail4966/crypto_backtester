# Agent D — Backend + Database Solutions

**Sources:** `A_BACKEND_ISSUES.md`, `C_SEVERITY_DEPENDENCY.md`  
**Consumers:** Agent F (implementation), Agent H (FE coordination)  
**Scope:** Design only — no code changes in this artifact.  
**Stack assumptions:** FastAPI + psycopg (autocommit off) + TimescaleDB; existing `get_db()` / repository commit patterns.

---

## Wave map (from Agent C)

| Wave | BE issues |
|------|-----------|
| **1** | BE-003, BE-002, BE-024, BE-016, BE-001, BE-004, BE-008, BE-007, BE-017 |
| **2** | BE-005, BE-006, BE-011, BE-009 |
| **3** | BE-012, BE-014, BE-013, BE-015, BE-018, BE-019, BE-020, BE-023, BE-010 |
| **4** | BE-021, BE-022 |

---

### BE-001 — Scan persist never commits (API path)
- Severity / Wave: High / Wave 1 (rank 5)
- Solution A: Call `conn.commit()` in `ScanRepository.insert()` after successful `INSERT … RETURNING`, matching `BacktestRepository` / watchlist / user repos.
- Solution B: Centralize commit in `get_db()` (commit on clean exit, rollback on exception) so all request-scoped repos inherit transactional commit without per-method `commit()`.
- **Recommended:** A (why: smallest fix aligned with existing repository commit convention; B is a larger behavioral change across all routers and needs a deliberate transaction redesign.)
- Implementation sketch:
  - Add `conn.commit()` after successful insert in `ScanRepository.insert`.
  - Ensure scan service only sets `persisted=True` when insert succeeds; on DB failure return `persisted=False` or error.
  - Add an integration test: `POST /scan` → row exists in `app.scan_runs` after response.
- Files: `backend/api/repositories/scan_repository.py`, `backend/api/services/scan_service.py`, tests under `backend/tests/api/`
- FE coordination: Unblocks FE-006 (screener UI); no FE contract change beyond honest persistence. Pair with BE-023 for retrieve.

---

### BE-002 — Account takeover via `/auth/claim` + passwordless `POST /users`
- Severity / Wave: Critical / Wave 1 (rank 2)
- Solution A: Fail-closed identity hardening — remove or disable public passwordless `POST /users`; remove `/auth/claim` (or gate it behind a one-time email proof token); keep register/login only with password + email.
- Solution B: Keep claim but require proof-of-email (signed claim token emailed, short TTL) and rate-limit claim/register heavily; deprecate passwordless create.
- Solution C: Admin-only claim migration tool (CLI) for legacy null-hash users; no public claim endpoint.
- **Recommended:** A (+ C for any remaining null-hash rows) (why: fail-closed removes the takeover surface immediately without needing email infra; C covers ops migration for legacy rows.)
- Implementation sketch:
  - Delete or 410 `/auth/claim`; remove claim from OpenAPI.
  - Make `POST /users` require password (or remove it and keep only `POST /auth/register`).
  - Reject create when `password_hash` would be null.
  - Ops: one-shot script to list null-hash users; set passwords via admin reset or force re-register.
  - Coordinate error shapes with BE-024 in the same PR.
- Files: `backend/api/routers/auth.py`, `backend/api/routers/users.py`, `backend/api/services/auth_service.py`, `backend/api/services/user_service.py`, `backend/api/schemas/users.py`, OpenAPI docs, tests
- FE coordination: FE-004 must stop any silent claim/`dev@local` passwordless path; register/login only. Ship BE-002 + FE-004 contract in the same release window.

---

### BE-003 — Hardcoded default JWT secret
- Severity / Wave: Critical / Wave 1 (rank 1)
- Solution A: Fail closed — `jwt_secret()` raises / process refuses to start if `JWT_SECRET` unset when `ENV`/`APP_ENV` is not `dev`/`local`; allow a clearly labeled local-only default only when `APP_ENV=dev`.
- Solution B: Always require `JWT_SECRET` (no default ever); document in `.env.example` and CI.
- **Recommended:** A (why: pragmatic for local DX while fail-closed for any shared/prod deploy; B is stricter but breaks zero-config local unless every developer sets env.)
- Implementation sketch:
  - Introduce `app_env()` (`dev` | `staging` | `prod`).
  - In non-dev: missing/weak/`dev-only-*` secret → raise at import/startup.
  - Reject known placeholder secrets even if set.
  - Document required env in deploy docs / Render / Docker compose.
- Files: `backend/api/settings.py`, `backend/api/main.py` (startup check), `.env.example`, deploy docs
- FE coordination: Indirect — BE-003 unblocks trustworthy JWT for FE-002/FE-003/FE-004; no API shape change. Rotate secret after deploy so old forged tokens die.

---

### BE-004 — Unauthenticated expensive compute (DoS / cost)
- Severity / Wave: High / Wave 1 (rank 6); depends on BE-003
- Solution A: Require JWT on backtest, scan, replay, live WS, and `/ai/*`; add hard caps (max window length, max symbols per scan, max concurrent WS per user); optional simple in-process rate limit by `user_id`/IP.
- Solution B: Keep public read-ish paths but put expensive endpoints behind auth + Redis/shared rate limiter + queue for backtest/scan/AI.
- **Recommended:** A (why: fits current stack without new infra; auth + caps stop the worst abuse; queue/Redis can wait for scale.)
- Implementation sketch:
  - Add `Depends(get_current_user)` (or WS token query/header) to listed routers.
  - Settings: `SCAN_MAX_SYMBOLS`, `BACKTEST_MAX_WINDOW_SEC`, `AI_MAX_RPM`, `WS_MAX_CONNECTIONS_PER_USER`.
  - Reject oversized windows/symbol lists with `VALIDATION` errors before compute.
  - For AI: refuse when no key OR always require auth even with mock provider.
- Files: `backend/api/routers/{backtest,scan,replay,ai}.py`, `backend/api/ws/{live,replay}.py`, `backend/api/settings.py`, schemas/services for caps, tests
- FE coordination: FE-006 and any anonymous callers must send Bearer tokens once gated; coordinate with FE-004 auth UX. Live/replay WS need token on connect (query `?token=` or first-message auth — pick one and document for FE-005/FE-008).

---

### BE-005 — Spoofable `user_id` on backtest runs
- Severity / Wave: High / Wave 2 (rank 10); depends on BE-003
- Solution A: Remove `user_id` from `BacktestCreateRequest`; set `backtest_runs.user_id` from JWT subject only (null if endpoint remains optional-auth — prefer required auth per BE-004).
- Solution B: Keep optional body field but ignore it when JWT present; reject if body `user_id` ≠ JWT without auth.
- **Recommended:** A (why: fail-closed — clients cannot forge attribution; simpler contract.)
- Implementation sketch:
  - Drop field from schema / OpenAPI.
  - `BacktestService.run` takes `current_user.id` from router dependency.
  - Migration not required (column already exists).
  - Update tests that posted client `user_id`.
- Files: `backend/api/schemas/backtest.py`, `backend/api/routers/backtest.py`, `backend/api/services/backtest_service.py`, tests
- FE coordination: FE-007 / backtest client must stop sending `user_id`; rely on token. Breaking request-shape change — same release as auth gate.

---

### BE-006 — Replay sessions have no owner; UUID is capability URL
- Severity / Wave: High / Wave 2 (rank 11); depends on BE-003
- Solution A: Add `user_id` column + FK; require JWT on create/get/delete and WS; enforce ownership on every access.
- Solution B: Treat session UUID as a high-entropy capability secret (no DB owner) + require auth to create; still bind delete/WS to creator via signed cookie/JWT claim list.
- **Recommended:** A (why: real ownership matches watchlist patterns and FE error handling; capability URLs remain guessable-or-leaked hijack risk.)
- Implementation sketch:
  - New migration: `ALTER TABLE app.replay_sessions ADD COLUMN user_id UUID REFERENCES app.users(id)` (nullable briefly for backfill, then NOT NULL for new rows).
  - Set `user_id` on create from JWT.
  - REST + WS: `get_current_user` / token; 403/404 on mismatch (prefer 404 to avoid existence leak).
  - Optionally GC orphan sessions with null owner.
- Files: new `V0xx__replay_owner.sql`, `backend/api/routers/replay.py`, `backend/api/ws/replay.py`, replay store/service/repo, tests
- FE coordination: FE-008/FE-009 must send Bearer (or agreed WS token) and handle 401/403; do not treat session id alone as auth. Land with BE-018 on same handler.

---

### BE-007 — Backtest/scan unix windows truncated to calendar dates
- Severity / Wave: High / Wave 1 (rank 8)
- Solution A: Replace `_unix_to_iso_date()` with full timestamptz ISO (same as candle service `_unix_to_iso`) for start/end binds.
- Solution B: Pass integer unix seconds into SQL (`to_timestamp(%s)`) and avoid string date formatting entirely.
- **Recommended:** A (why: minimal diff, already proven on candle/chart path; restores inclusive unix contract quickly.)
- Implementation sketch:
  - Change helpers in `backtest_service` / `scan_service` to emit full ISO with time+UTC.
  - Confirm query binds use `timestamptz` comparisons (already do).
  - Add tests: window `end` includes bars on the end calendar day after midnight; start respects intra-day floor.
  - Golden-check vs candle query for same `[from,to]`.
- Files: `backend/api/services/backtest_service.py`, `backend/api/services/scan_service.py`, possibly shared util, tests
- FE coordination: FE-007 overlays/metrics become trustworthy; no FE API change if clients already send unix seconds. Document that contract is now honored.

---

### BE-008 — Candle/chart `limit` applied after full-range load
- Severity / Wave: High / Wave 1 (rank 7)
- Solution A: Push `LIMIT` (+ deterministic `ORDER BY ts`) into SQL for both raw and derived candle queries; compute `next_from` from last returned bar.
- Solution B: Keyset pagination only (`ts >= from AND ts < to` with limit) and require clients to page; reject ranges wider than `limit * timeframe` without cursors.
- **Recommended:** A (why: preserves existing `from`/`to`/`limit`/`next_from` contract while fixing OOM; B is stricter but more breaking for FE.)
- Implementation sketch:
  - Extend `SELECT_*_CANDLES_BY_RANGE` (and derived) with `ORDER BY bucket/ts ASC LIMIT %s`.
  - Apply limit in repository/`get_candles`, not after full DataFrame build.
  - Chart-data path: same SQL limit; for empty windows return empty bars + explicit flag (e.g. `empty: true` / no silent latest-fallback) — coordinate FE-011.
  - Cap `to - from` as defense-in-depth (optional with BE-004).
- Files: `backend/data/repository/queries.py`, `backend/data/repository/candle_repository.py`, `backend/data/loader.py`, `backend/api/services/candle_service.py`, chart_data service, tests
- FE coordination: FE-010/FE-011 — stable `start`/`next_from` under SQL limit; prefer empty-window response over latest-fallback so FE does not corrupt prior chunks.

---

### BE-009 — Derived TF includes incomplete in-progress buckets
- Severity / Wave: High / Wave 2 (rank 13)
- Solution A: Exclude incomplete buckets in SQL — e.g. require `COUNT(*)` of 1m bars ≥ expected bars for bucket, or `bucket_end <= max(closed_1m_ts)+1m`.
- Solution B: Return incomplete bucket but mark `closed: false` / `partial: true` and teach consumers (live/backtest/scan) to ignore partials unless opted in.
- **Recommended:** A (why: backtest/scan/live currently assume closed bars; excluding partials is fail-safe and avoids FE/engine branching everywhere. B is better long-term UX for live “forming candle” but needs FE-005 contract work.)
- Implementation sketch:
  - Amend `SELECT_DERIVED_CANDLES_BY_RANGE` (and metadata variants) with HAVING / WHERE on complete buckets.
  - Define expected 1m count per TF (`1h`→60, `1d`→1440, …); for `1M` use calendar-aware rule once BE-010 lands, or temporarily exclude open month.
  - Live WS: only emit when closed bar advances.
  - Tests for “now” window: last bucket omitted until complete.
- Files: `backend/data/repository/queries.py`, candle repository, live WS path, backtest/scan loaders, tests
- FE coordination: Blocks FE-005; FE should not assume a live partial bar until/unless Solution B is chosen later. FE-007 near-now overlays also depend on this.

---

### BE-010 — `1M` semantics inconsistent (calendar month vs 30 days)
- Severity / Wave: Medium / Wave 3 (rank 22)
- Solution A: Standardize on calendar month everywhere — Timescale `1 month` buckets; replace 30-day constants in `timeframes.py` / fetcher with calendar month helpers (or “approx for warmup only” clearly named and not used for seek boundaries).
- Solution B: Standardize on 30-day “month” — change SQL bucket to `30 days` and document non-calendar months.
- **Recommended:** A (why: SQL already uses calendar months; aligning API/fetcher to calendar matches user expectations for monthly charts.)
- Implementation sketch:
  - Add helpers: month floor/ceil, shift by N months in UTC.
  - Update warmup/seek/advance/`TIMEFRAME_MS["1M"]` consumers to use calendar math (ms becomes approximate only where unavoidable).
  - Document in `/meta/timeframes`.
  - Tests around month boundaries (Jan 31 → Feb).
- Files: `backend/api/services/timeframes.py`, `backend/data/fetcher.py`, `backend/data/repository/candle_repository.py`, meta router, tests
- FE coordination: FE-016 should load `/meta/timeframes` only after this lands before exposing `1M` in the UI.

---

### BE-011 — Migrations race under concurrent startup
- Severity / Wave: High / Wave 2 (rank 12)
- Solution A: Take a Postgres session advisory lock (`pg_advisory_lock`) at start of `run_migrations`, release when done; other instances block then no-op on already-applied versions.
- Solution B: Run migrations only from a single init job/container (Kubernetes migrate Job / one-shot entrypoint); API containers never migrate.
- **Recommended:** A (why: works with current “migrate on API startup” without deploy topology change; B is cleaner ops long-term but needs platform work.)
- Implementation sketch:
  - In `run_migrations`, `SELECT pg_advisory_lock(<fixed_key>)` before reading pending; `unlock` in `finally`.
  - Keep per-migration transaction semantics as today.
  - Test with concurrent callers (two threads/processes) applying pending Vxxx once.
- Files: `backend/data/migrations/migrator.py`, tests
- FE coordination: None. Prerequisite for safe Wave 3/4 schema migrations (BE-014/021/022).

---

### BE-012 — Register/create user not transactional with default watchlist
- Severity / Wave: Medium / Wave 3 (rank 14)
- Solution A: Single DB transaction — create user + default watchlist + symbols on one connection; one `commit()` at end; rollback on any failure.
- Solution B: Compensating cleanup (delete user if watchlist create fails) without shared transaction.
- **Recommended:** A (why: true atomicity with psycopg; B can still leave orphans under crash mid-compensate.)
- Implementation sketch:
  - Stop intermediate `commit()` inside user/watchlist repo methods when called from provision path (add `commit: bool = True` flag or a unit-of-work helper).
  - `AuthService.register` / user create: create user → create Default watchlist → `set_symbols` → commit once.
  - Test crash injection / forced failure after user insert → no user row remains.
- Files: `backend/api/services/auth_service.py`, `backend/api/services/user_service.py`, `user_repository.py`, `watchlist_repository.py`, tests
- FE coordination: FE-004 onboarding can assume Default watchlist always exists after successful register.

---

### BE-013 — Setting `is_default` can clear all defaults if update misses
- Severity / Wave: Medium / Wave 3 (rank 16); depends on BE-014 for blast radius
- Solution A: Reorder — `UPDATE` first; only `CLEAR_DEFAULT` for *other* rows when update affected 1 row; otherwise rollback.
- Solution B: Single SQL statement using a CTE/`UPDATE … FROM` that clears others and sets target atomically; abort if no row matched.
- **Recommended:** B (why: one round-trip, atomic, hard to misuse; A also fine if B is awkward with current query style.)
- Implementation sketch:
  - Replace clear-then-update with transactional CTE or `UPDATE … WHERE id AND user_id RETURNING`; if no row → rollback, raise 404.
  - Clear other defaults only after successful target update (same transaction).
  - Tests: mismatched id leaves previous default intact.
- Files: `backend/api/repositories/watchlist_repository.py`, `backend/api/repositories/queries.py`, tests
- FE coordination: FE-017 default-toggle UI should wait until BE-013+BE-014 land.

---

### BE-014 — No uniqueness for “one default watchlist per user”
- Severity / Wave: Medium / Wave 3 (rank 15); depends on BE-011
- Solution A: Partial unique index `UNIQUE (user_id) WHERE is_default` after cleaning existing duplicates.
- Solution B: Enforce only in application with `SELECT FOR UPDATE` — no DB constraint.
- **Recommended:** A (why: DB is source of truth under concurrency; app-only checks still race.)
- Implementation sketch:
  - Data fix migration: for users with multiple defaults, keep oldest/newest one; set others false.
  - `CREATE UNIQUE INDEX … ON app.watchlists (user_id) WHERE is_default`.
  - Optionally require every user has ≥1 default via app invariant (not easily CHECKed across rows).
- Files: new migration SQL, watchlist repository (handle unique violation → 409), tests
- FE coordination: FE-017; reduces ambiguous default list for clients.

---

### BE-015 — Email uniqueness is case-sensitive; no format validation
- Severity / Wave: Medium / Wave 3 (rank 17); depends on BE-002
- Solution A: Normalize to lowercase on write/read; add `citext` or unique index on `lower(email)`; Pydantic `EmailStr` (or regex) validation.
- Solution B: Store original casing for display but unique on `lower(email)` generated column / functional unique index.
- **Recommended:** A (why: simplest; emails are case-insensitive in practice; less schema novelty than citext if we just lowercase.)
- Implementation sketch:
  - Migrate: lowercase existing emails; resolve collisions manually/script.
  - Unique index on `lower(email)` if keeping TEXT, or normalize in app + keep UNIQUE.
  - Schemas: validate format; strip + lower before insert/login/lookup.
  - Login/register always query with normalized email.
- Files: migration, `backend/api/schemas/auth.py`, `users.py`, auth/user services & repos, tests
- FE coordination: FE-004 — show format validation errors; login emails case-insensitive.

---

### BE-016 — `GET /users` enumerates all users; `GET /users/{id}` public
- Severity / Wave: High / Wave 1 (rank 4); depends on BE-003; coordinate FE-002
- Solution A: Remove list-all (or admin-only); replace public get with authenticated `GET /auth/me` or `GET /users/me`; `GET /users/{id}` requires JWT + same-user (or 404).
- Solution B: Keep `GET /users/{id}` but require JWT and same-user; delete `GET /users` entirely.
- **Recommended:** A (why: `/me` is the right bootstrap proof for FE-002 and removes enumeration; matches modern auth UX.)
- Implementation sketch:
  - Add `GET /auth/me` (or `/users/me`) → current user DTO without password hash.
  - Lock down or remove collection GET.
  - Path GET: `Depends(get_current_user)` + `require_same_user`.
  - Update OpenAPI / Phase 11 matrix.
- Files: `backend/api/routers/users.py`, `backend/api/routers/auth.py`, deps, tests, OpenAPI
- FE coordination: **Hard dependency for FE-002** — bootstrap must switch from public `GET /users/{id}` to `/me` in the same release; FE-003 uses 401 from `/me` as session-invalid signal.

---

### BE-017 — CORS localhost regex enabled by default
- Severity / Wave: High / Wave 1 (rank 9)
- Solution A: Default `CORS_ALLOW_LOCALHOST` to false; enable only when `APP_ENV=dev` or explicit true.
- Solution B: Remove regex entirely; rely solely on explicit `CORS_ORIGINS` list.
- **Recommended:** A (why: fail-closed default for prod-reachable APIs while preserving one-flag local DX for Vite port churn.)
- Implementation sketch:
  - Change default in `cors_allow_localhost_regex()` to off unless env explicitly enables or `APP_ENV=dev`.
  - Keep `CORS_ORIGINS` as primary allowlist.
  - Document production: set origins explicitly; never enable localhost regex.
- Files: `backend/api/settings.py`, `backend/api/main.py` (if needed), `.env.example`, deploy docs
- FE coordination: Local Vite must set `CORS_ALLOW_LOCALHOST=true` or include origin in `CORS_ORIGINS`; prod FE origin only in allowlist.

---

### BE-018 — Replay WS: uncaught bad JSON; long-held DB connection
- Severity / Wave: Medium / Wave 3 (rank 18); depends on BE-006 (same handler)
- Solution A: try/except around `json.loads` (send error frame / continue); open DB connections per message or short critical section, not for WS lifetime.
- Solution B: Move replay state to in-memory store + periodic checkpoint (existing idle checkpoint) so WS loop rarely needs DB.
- **Recommended:** A (+ lean on existing checkpoint pattern) (why: matches live WS robustness; avoids connection pool exhaustion without a large architecture rewrite. B can follow if load demands.)
- Implementation sketch:
  - Mirror live WS JSON error handling.
  - Refactor: load session → release conn; on checkpoint/command needing DB, `connect()` briefly.
  - Ensure BE-006 auth check happens before long loops.
- Files: `backend/api/ws/replay.py`, possibly replay store, tests
- FE coordination: FE-008/FE-009 — malformed client messages should get error frames, not silent socket death; reconnect logic benefits from stable handler.

---

### BE-019 — Live WS opens a new DB connection per symbol per poll
- Severity / Wave: Medium / Wave 3 (rank 19)
- Solution A: One shared connection (or small pool) per WS client connection; reuse across symbols/polls; batch latest-bar queries (`WHERE symbol = ANY(%)`).
- Solution B: Introduce app-wide psycopg pool (`ConnectionPool`) used by HTTP + WS.
- **Recommended:** A first, B as follow-up (why: A fixes the hot path with minimal blast radius; B is the right long-term platform change but touches all `connect()` call sites.)
- Implementation sketch:
  - In live WS handler, open one conn for the socket lifetime (or checkout from pool).
  - `_latest_bar` uses that conn; prefer one multi-symbol query per tick.
  - Close/return conn on WS disconnect.
  - Optional: later add `data.db.pool`.
- Files: `backend/api/ws/live.py`, optionally `backend/data/db.py`, tests
- FE coordination: Prerequisite for FE-005; do not wire FE live until this + BE-009 are done.

---

### BE-020 — In-memory AI clarify sessions + multi-worker loss
- Severity / Wave: Medium / Wave 3 (rank 20); depends on BE-004
- Solution A: Persist clarification sessions in Postgres (`app.ai_clarify_sessions`) with `user_id`, TTL expiry, UUID PK; bind continue to same user.
- Solution B: Redis session store with TTL + user binding (if Redis already planned).
- **Recommended:** A (why: no new infra; fits Timescale/Postgres stack already used for app state.)
- Implementation sketch:
  - Migration for sessions table (payload JSONB, user_id, expires_at).
  - Replace `ClarificationSessionStore` backend with DB implementation; keep interface.
  - Require auth (BE-004); reject continue if `user_id` mismatch.
  - Periodic delete expired rows.
- Files: new migration, `backend/ai/sessions.py`, `backend/api/services/ai_service.py`, tests
- FE coordination: FE-006 AI clarify UI — sessions survive multi-worker; must send auth; handle expiry errors cleanly.

---

### BE-021 — `data_gaps` weak constraints / duplicate opens
- Severity / Wave: Low / Wave 4 (rank 23); depends on BE-011
- Solution A: Add FK to symbols, CHECK on status, and unique constraint / exclusion on open overlapping ranges (e.g. unique open per symbol where status=open, plus app merge logic).
- Solution B: Strengthen reconcile in `gaps.py` only (merge overlaps in Python) without DB constraints.
- **Recommended:** A (why: constraints + reconcile together stop duplicates under concurrency; B alone still races.)
- Implementation sketch:
  - Migration: FK, `CHECK (status IN (...))`, unique or exclude constraint for open gaps.
  - Dedupe existing rows before applying unique.
  - Update `gaps.py` reconcile to merge overlaps before insert.
- Files: new migration (after V004 lineage), `backend/data/gaps.py`, tests
- FE coordination: None (internal sync quality).

---

### BE-022 — Status / state columns lack CHECK constraints
- Severity / Wave: Low / Wave 4 (rank 24); depends on BE-011
- Solution A: Add PostgreSQL `CHECK (status/state IN (...))` on replay/backtest/scan/gaps columns matching app literals.
- Solution B: Use Postgres ENUM types for each status column.
- **Recommended:** A (why: CHECKs are easy to evolve via migration; ENUMs are awkward to alter in Postgres.)
- Implementation sketch:
  - Inventory allowed literals from services/repos.
  - One migration adding CHECKs; validate existing rows first.
  - Keep app constants as single source mirrored in migration comments/tests.
- Files: new migration SQL, optionally shared Python enums module, tests
- FE coordination: None unless error codes change on invalid writes (they shouldn’t for normal API).

---

### BE-023 — Scan repository `get()` unused; no HTTP retrieve
- Severity / Wave: Medium / Wave 3 (rank 21); depends on BE-001
- Solution A: Add `GET /scan/{scan_id}` (auth-required) returning persisted run; wire existing `ScanRepository.get`.
- Solution B: Embed full result only in POST response and treat DB as write-only audit (no GET).
- **Recommended:** A (why: repository already has `get`; completes API contract and unblocks FE screener history.)
- Implementation sketch:
  - Router + response schema from `ScanRunRow`.
  - 404 when missing; auth per BE-004; optional future ownership column.
  - OpenAPI update; integration test POST then GET.
- Files: `backend/api/routers/scan.py`, schemas, OpenAPI, tests
- FE coordination: FE-006 can load/history scan results after BE-001+BE-023.

---

### BE-024 — Auth claim / login reveal account state (enumeration)
- Severity / Wave: Medium / Wave 1 (rank 3); depends on BE-002
- Solution A: After removing/redesigning claim (BE-002), make register/login/claim-replacement return uniform errors (`INVALID_CREDENTIALS` / generic `AUTH_FAILED`) without distinguishing existence vs password state; constant-time-ish responses where practical.
- Solution B: Keep distinct codes but rate-limit + CAPTCHA heavily.
- **Recommended:** A (why: removes the oracle; fits fail-closed claim removal; B still leaks to patient attackers.)
- Implementation sketch:
  - Align `EMAIL_EXISTS` policy: either generic “cannot register” or anti-enumeration register that always returns success fake (product choice — prefer generic conflict without confirming other fields).
  - Login already generic — keep it.
  - Ensure removed claim path cannot return `USER_NOT_FOUND` vs `PASSWORD_ALREADY_SET`.
  - Tests for identical status codes across unknown vs known emails where required.
- Files: `backend/api/services/auth_service.py`, schemas/error codes, tests
- FE coordination: FE-004 must handle new uniform error codes; do not branch UX on existence oracles.

---

## Cross-cutting recommendations for Agent F

1. **Wave 1 security bundle:** Ship BE-003 → BE-002+BE-024 → BE-016 together with FE-002/FE-004 contract agreement before enabling shared deploys.
2. **Commit convention:** Prefer explicit repository `commit()` (current style) until a deliberate Unit-of-Work/`get_db` commit policy is designed (see BE-001 B / BE-012).
3. **Auth on compute:** BE-004 gates should land before FE wires screener/AI/live (FE-005/FE-006).
4. **Migrations:** Do BE-011 before any Wave 3/4 constraint migrations.
5. **Empty chart windows:** When fixing BE-008, explicitly define empty-range behavior for FE-011 (empty + flag ≫ silent latest fallback).

---

## Counts

| Wave | Issues |
|------|--------|
| 1 | 9 |
| 2 | 4 |
| 3 | 9 |
| 4 | 2 |
| **Total** | **24** |

Each issue has ≥2 solutions and exactly one **Recommended** marked above.
