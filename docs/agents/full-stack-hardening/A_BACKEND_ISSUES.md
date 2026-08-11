# Agent A — Backend + Database Issues

## Backend + Database Issues

### BE-001 — Scan persist never commits (API path)
- **Area:** `backend/api/repositories/scan_repository.py`, `backend/api/deps.py`
- **Description:** `ScanRepository.insert()` executes `INSERT` into `app.scan_runs` but never calls `conn.commit()`. `get_db()` opens a connection and only `close()`s it, so the transaction is rolled back. CLI `run_scan.py` commits explicitly; the HTTP path does not. Response still sets `persisted=True` / returns `scan_id`.
- **Impact:** Scan results appear saved but vanish; any future `GET` would 404; audit trail is false.
- **Category:** bug

### BE-002 — Account takeover via `/auth/claim` + passwordless `POST /users`
- **Area:** `backend/api/routers/auth.py`, `backend/api/services/auth_service.py`, `backend/api/routers/users.py`
- **Description:** `POST /users` is public and creates users with `password_hash IS NULL`. `POST /auth/claim` sets a password for any such account given only `email` (no email proof / token). Anyone who knows or squats an email can claim the account and receive a JWT.
- **Impact:** Full account takeover of legacy/passwordless users; email squatting blocks legitimate registration (`EMAIL_EXISTS`).
- **Category:** security

### BE-003 — Hardcoded default JWT secret
- **Area:** `backend/api/settings.py` (`jwt_secret()`)
- **Description:** Default is `"dev-only-change-me-crypto-backtester"` when `JWT_SECRET` is unset. Tokens signed with a public, fixed secret are forgeable.
- **Impact:** In any shared/prod deploy without env override, attackers can mint JWTs for any `user_id` and pass ownership checks on watchlists / user PATCH/DELETE.
- **Category:** security

### BE-004 — Unauthenticated expensive compute (DoS / cost)
- **Area:** `backend/api/routers/backtest.py`, `backend/api/routers/scan.py`, `backend/api/routers/ai.py`, `backend/api/ws/live.py`
- **Description:** Phase 11 matrix leaves backtest, scan, replay, live WS, and `/ai/*` public. No rate limits, no max window/symbol caps on scan/backtest (unlike candle `limit`). AI calls upstream LLM when `AI_LLM_API_KEY` is set.
- **Impact:** CPU/memory/DB exhaustion via large windows or many symbols; LLM bill abuse; live WS open connection storms.
- **Category:** security / reliability

### BE-005 — Spoofable `user_id` on backtest runs
- **Area:** `backend/api/schemas/backtest.py`, `backend/api/services/backtest_service.py`
- **Description:** `BacktestCreateRequest.user_id` is optional and accepted from the client with no JWT check; stored on `app.backtest_runs.user_id`.
- **Impact:** Attribution forgery; polluted per-user history if that column is trusted later.
- **Category:** security / data-integrity

### BE-006 — Replay sessions have no owner; UUID is capability URL
- **Area:** `backend/api/routers/replay.py`, `backend/api/ws/replay.py`, `backend/data/migrations/sql/V007__replay_sessions.sql`
- **Description:** `app.replay_sessions` has no `user_id`. Create/get/delete and `/ws/replay/{session_id}` require no auth. Schema comment still says “logging only until auth (Phase 11)” but ownership was never added.
- **Impact:** Anyone with (or guessing) a session id can read state, drive playback, or delete sessions; cross-user hijack of active replays.
- **Category:** security

### BE-007 — Backtest/scan unix windows truncated to calendar dates
- **Area:** `backend/api/services/backtest_service.py`, `backend/api/services/scan_service.py`, `backend/data/repository/queries.py`
- **Description:** Both use `_unix_to_iso_date()` → `date().isoformat()` then pass into `ts >= %s::timestamptz AND ts <= %s::timestamptz`. End date `"YYYY-MM-DD"` binds as midnight UTC, so nearly the entire end day is excluded. Start is floored to midnight, including earlier bars than requested. Candle/chart paths correctly use full ISO timestamps.
- **Impact:** Wrong candle sets → incorrect metrics, signals, scan matches; API contract says inclusive unix seconds but engine ignores time-of-day.
- **Category:** bug / api-contract

### BE-008 — Candle/chart `limit` applied after full-range load
- **Area:** `backend/api/services/candle_service.py`, `backend/data/repository/queries.py`
- **Description:** `get_candles()` loads the entire `[from, to]` via SQL with no `LIMIT`, builds all bars in memory, then truncates to `effective_limit` and sets `next_from`.
- **Impact:** Wide `from`/`to` (especially `1m`) can OOM or stall the API despite a small client limit; easy resource exhaustion.
- **Category:** performance / reliability

### BE-009 — Derived TF includes incomplete in-progress buckets
- **Area:** `backend/data/repository/queries.py` (`SELECT_DERIVED_CANDLES_BY_RANGE`), live/backtest consumers
- **Description:** Aggregation uses `time_bucket` with no filter requiring a full bucket (e.g. enough 1m bars for an hour/day). Sync stores only closed **1m** bars, so the current higher-TF bucket is still a partial aggregate.
- **Impact:** Live WS and reads on `1h`/`1d`/etc. treat a forming bar as a closed candle; backtests/scans near “now” can trade on incomplete bars.
- **Category:** bug / data-integrity

### BE-010 — `1M` semantics inconsistent (calendar month vs 30 days)
- **Area:** `backend/data/repository/candle_repository.py` (`"1M": "1 month"`), `backend/api/services/timeframes.py` (`30 * 24 * 60 * 60`), `backend/data/fetcher.py` (`TIMEFRAME_MS["1M"] = 30d`)
- **Description:** SQL derives months via Timescale `1 month`; API warmup/shift/advance and fetcher ms table use fixed 30-day approximations (explicitly noted in `timeframes.py`).
- **Impact:** Wrong warmup windows, pagination steps, and seek math for monthly charts vs actual bucket boundaries.
- **Category:** bug

### BE-011 — Migrations race under concurrent startup
- **Area:** `backend/data/migrations/migrator.py`
- **Description:** No advisory lock / `SKIP LOCKED`. Multiple API instances (or API + sync CLI) can apply the same pending migration concurrently; `INSERT` into `schema_migrations` can conflict after DDL partially applied.
- **Impact:** Failed deploys, half-applied schema, hard-to-recover migration state.
- **Category:** reliability / data-integrity

### BE-012 — Register/create user not transactional with default watchlist
- **Area:** `backend/api/services/auth_service.py`, `backend/api/services/user_service.py`, repositories
- **Description:** `UserRepository.create*` commits immediately; watchlist create / `set_symbols` commit separately. Failure mid-provision leaves a user without a default watchlist (or empty list).
- **Impact:** Broken onboarding state; clients assume a Default watchlist always exists.
- **Category:** data-integrity / reliability

### BE-013 — Setting `is_default` can clear all defaults if update misses
- **Area:** `backend/api/repositories/watchlist_repository.py` (`update`)
- **Description:** When `is_default` is truthy, `CLEAR_DEFAULT_WATCHLISTS` runs, then `UPDATE_WATCHLIST`. If the watchlist id/user mismatch returns no row, defaults were already cleared and commit still happens → zero defaults.
- **Impact:** User can end with zero default watchlists after a failed/mismatched update.
- **Category:** data-integrity / bug

### BE-014 — No uniqueness for “one default watchlist per user”
- **Area:** `backend/data/migrations/sql/V005__app_schema.sql`
- **Description:** `is_default` is a plain boolean; no partial unique index `UNIQUE (user_id) WHERE is_default`. Concurrent updates or bugs can leave multiple defaults.
- **Impact:** Ambiguous “default” list for clients.
- **Category:** data-integrity

### BE-015 — Email uniqueness is case-sensitive; no format validation
- **Area:** `backend/data/migrations/sql/V005__app_schema.sql`, `backend/api/schemas/auth.py`, `backend/api/schemas/users.py`
- **Description:** `email TEXT UNIQUE` treats `User@x` and `user@x` as different. Schemas only check string length, not email format / normalization.
- **Impact:** Duplicate logical accounts; login failures from case mismatch; weak identity hygiene.
- **Category:** data-integrity / security

### BE-016 — `GET /users` enumerates all users; `GET /users/{id}` public
- **Area:** `backend/api/routers/users.py`
- **Description:** Any valid JWT can list all users (emails/names). Single-user GET is unauthenticated by design (Phase 11).
- **Impact:** Privacy leak / user enumeration; aids claim attacks (BE-002).
- **Category:** security

### BE-017 — CORS localhost regex enabled by default
- **Area:** `backend/api/settings.py` (`cors_allow_localhost_regex`), `backend/api/main.py`
- **Description:** `CORS_ALLOW_LOCALHOST` defaults to `true`, allowing `http://localhost|127.0.0.1` any port with `allow_credentials=True`.
- **Impact:** If API is reachable from a browser in production without disabling this, local malicious pages can call credentialed APIs.
- **Category:** security

### BE-018 — Replay WS: uncaught bad JSON; long-held DB connection
- **Area:** `backend/api/ws/replay.py`
- **Description:** `json.loads(raw)` has no try/except (unlike live WS). Handler wraps the entire message loop in `with connect() as conn:`, holding one Postgres connection for the full WS lifetime.
- **Impact:** Malformed frames crash the handler; many concurrent replay sockets exhaust DB connections / starve HTTP.
- **Category:** reliability

### BE-019 — Live WS opens a new DB connection per symbol per poll
- **Area:** `backend/api/ws/live.py` (`_latest_bar`)
- **Description:** Each poll for each subscription calls `connect()` / `close()`. Default poll interval 2s × N symbols × M clients.
- **Impact:** Connection churn and DB load spikes under modest fan-out.
- **Category:** performance / reliability

### BE-020 — In-memory AI clarify sessions + multi-worker loss
- **Area:** `backend/ai/sessions.py`, `backend/api/services/ai_service.py`
- **Description:** Clarification state is process-local (`ClarificationSessionStore`). No sticky sessions assumed; multi-worker/uvicorn or restart drops `session_id`s. Sessions also lack user binding (anyone with id can continue).
- **Impact:** Flaky `/ai/clarify` in production; cross-user session guessing if ids leak.
- **Category:** reliability / security

### BE-021 — `data_gaps` weak constraints / duplicate opens
- **Area:** `backend/data/migrations/sql/V004__data_gaps.sql`, `backend/data/gaps.py`
- **Description:** No FK to symbols, no `CHECK (status IN (...))`, no unique key on open ranges. Reconcile only skips exact `(start_ts, end_ts)` matches, so overlapping differently bounded gaps duplicate.
- **Impact:** Duplicate retries, noisy gap table, no referential integrity to catalog.
- **Category:** data-integrity

### BE-022 — Status / state columns lack CHECK constraints
- **Area:** `V007` (`replay_sessions.state`), `V008` (`backtest_runs.status`), `V009` (`scan_runs.status`), `V004` (`data_gaps.status`)
- **Description:** Free-form `TEXT` with app-level literals only; invalid values can be written by bugs or raw SQL.
- **Impact:** Silent bad rows; clients/engines may mishandle unexpected states.
- **Category:** data-integrity

### BE-023 — Scan repository `get()` unused; no HTTP retrieve
- **Area:** `backend/api/repositories/scan_repository.py`, `backend/api/routers/scan.py`, OpenAPI `/api/v1/scan`
- **Description:** Only `POST /scan` exists. `SELECT_SCAN_RUN` / `ScanRepository.get` have no router. Combined with BE-001, persistence is both broken and unreadable.
- **Impact:** API contract incomplete; persisted scans (when fixed) still unreachable via API.
- **Category:** api-contract / dead-code

### BE-024 — Auth claim / login reveal account state (enumeration)
- **Area:** `backend/api/services/auth_service.py`
- **Description:** Claim returns `USER_NOT_FOUND` vs `PASSWORD_ALREADY_SET`; login uses a generic credential error (good) but claim/register distinguish existence.
- **Impact:** Email enumeration and targeting of passwordless accounts for BE-002.
- **Category:** security

---

## Scope covered

Reviewed:
- **API surface:** `backend/api/main.py`, deps/auth/settings/exceptions, routers (`auth`, `users`, `watchlists`, `symbols`, `candles`, `chart_data`, `indicators`, `replay`, `backtest`, `scan`, `ai`, `meta`), WS (`live`, `replay`)
- **Services/repos:** auth/user/watchlist/symbol/candle/chart/indicator/backtest/scan/ai/replay engine+store; SQL in `api/repositories/queries.py`
- **DB:** migrations `V001`–`V010`, migrator, `data/db.py`, candle/gap repositories & queries, sync/loader/fetcher gap path
- **Related:** Phase 11 HLD auth matrix, OpenAPI auth/scan snippets, AI sessions/providers, screener pipeline hooks
- **Not reviewed in depth:** frontend UI (except API contract expectations), pure SMC/structure/pattern math internals without DB I/O
