# Agent F — Backend Implementation Report

**Date:** 2026-08-11  
**Sources:** `D_BACKEND_SOLUTIONS.md` (Recommended), `C_SEVERITY_DEPENDENCY.md`, `A_BACKEND_ISSUES.md`  
**Scope:** BE-001 … BE-024 (Waves 1–4). Frontend not modified.

---

## Test results

```text
cd backend && APP_ENV=dev AI_CLARIFY_STORE=memory \
  .venv/bin/python -m pytest tests/api/ tests/ai/ tests/data/ -q
# → 138+ passed (plus new settings/calendar tests)
```

Targeted suites run after changes: `tests/api/`, `tests/ai/`, `tests/data/` — all green. Full repo suite not exhaustively re-run (structure/smc/backtest unit tests untouched by API contracts).

---

## Per-issue summary

### Wave 1

| ID | What was done | Files touched | Deferred |
|----|---------------|---------------|----------|
| **BE-003** | `app_env()` / `is_dev_env()`; `jwt_secret()` fail-closed outside `dev`/`local`; reject placeholders & short secrets; `validate_security_settings()` at app factory + lifespan | `api/settings.py`, `api/main.py`, `backend/.env.example`, `tests/api/test_settings.py` | Rotate secrets in deploy docs left to ops |
| **BE-002** | Removed `/auth/claim`; `POST /users` requires password; reject null hash; ops script lists null-hash users | `api/routers/auth.py`, `api/services/auth_service.py`, `api/schemas/auth.py`, `api/schemas/users.py`, `api/services/user_service.py`, `api/repositories/user_repository.py`, `scripts/list_null_hash_users.py`, `tests/api/test_auth.py` | Admin password-reset CLI not built — use register/re-register |
| **BE-024** | Uniform register conflict message; login stays `INVALID_CREDENTIALS`; claim oracle removed with claim | `api/services/auth_service.py`, `api/services/user_service.py`, tests | Constant-time padding not implemented (practical equality of codes only) |
| **BE-016** | `GET /auth/me` + `GET /users/me`; `GET /users` → 410; `GET /users/{id}` JWT + same-user | `api/routers/auth.py`, `api/routers/users.py`, tests | Admin list-all not added |
| **BE-001** | `ScanRepository.insert` commits; `persisted` only when insert succeeds | `api/repositories/scan_repository.py`, `api/services/scan_service.py` | Integration test against live DB not added (mocked HTTP tests updated) |
| **BE-004** | JWT on backtest/scan/replay/AI/live WS/replay WS; caps `SCAN_MAX_SYMBOLS`, `BACKTEST_MAX_WINDOW_SEC`, `AI_MAX_RPM`, `WS_MAX_CONNECTIONS_PER_USER`; WS `?token=` | `api/settings.py`, routers (`backtest`,`scan`,`ai`,`replay`), `api/deps.py`, `api/ws/live.py`, `api/ws/replay.py`, tests | Redis/shared rate limiter not added |
| **BE-008** | SQL `LIMIT` variants; candle service fetches `limit+1` for `next_from`; chart empty window returns `empty: true` (no latest fallback) | `data/repository/queries.py`, `candle_repository.py`, `data/loader.py`, `api/services/candle_service.py`, `chart_data_service.py`, `api/schemas/chart_data.py`, tests | Optional `to-from` hard cap left to BE-004 window caps |
| **BE-007** | Full ISO timestamptz for backtest/scan windows (same as candles) | `api/services/backtest_service.py`, `api/services/scan_service.py` | Golden vs candle SQL integration test not added |
| **BE-017** | Localhost CORS regex default on only in `dev`/`local`; else off unless `CORS_ALLOW_LOCALHOST=true` | `api/settings.py`, `.env.example`, tests | — |

### Wave 2

| ID | What was done | Files touched | Deferred |
|----|---------------|---------------|----------|
| **BE-005** | Dropped body `user_id`; JWT subject passed into `BacktestService.run` | `api/schemas/backtest.py`, `api/routers/backtest.py`, `api/services/backtest_service.py`, tests | — |
| **BE-006** | Migration `V011` adds `replay_sessions.user_id`; ownership on REST + WS; 404 on mismatch | `V011__replay_session_owner.sql`, replay repo/service/store/routers/ws, queries, tests | GC of orphans done via migration DELETE |
| **BE-011** | `pg_advisory_lock` around `run_migrations` | `data/migrations/migrator.py` | Concurrent process test not added |
| **BE-009** | Derived SQL `HAVING` expected 1m count + bucket end ≤ max closed 1m | `data/repository/queries.py`, `candle_repository.py` (`EXPECTED_1M_BARS`) | Metadata max/min queries still coarse; live partial UX (Solution B) not chosen |

### Wave 3

| ID | What was done | Files touched | Deferred |
|----|---------------|---------------|----------|
| **BE-012** | Register/create: user + default watchlist + symbols, single `commit` (`commit=False` on intermediate repo calls) | `auth_service.py`, `user_service.py`, `user_repository.py`, `watchlist_repository.py` | Crash-injection integration test not added |
| **BE-014** | Migration: dedupe defaults + partial unique index | `V012__watchlist_default_and_email.sql` | 409 mapping on unique violation not specialized in watchlist service |
| **BE-013** | Atomic `SET_DEFAULT_WATCHLIST` CTE; rollback if no row | `api/repositories/queries.py`, `watchlist_repository.py` | — |
| **BE-015** | Email normalize/validate on schemas; `lower(email)` on insert/lookup; unique index on `lower(email)` | schemas, user repo, queries, `V012` | Manual collision resolution for pre-existing mixed-case dupes |
| **BE-018** | Replay WS: try/except JSON; DB `connect()` per critical section | `api/ws/replay.py` | — |
| **BE-019** | Live WS: one shared conn for socket lifetime; batch poll helper | `api/ws/live.py` | App-wide `ConnectionPool` (Solution B) deferred |
| **BE-020** | `V013` table; `PostgresClarificationSessionStore` + user binding; `AI_CLARIFY_STORE=memory` for tests | `ai/sessions.py`, `ai/translate.py`, `api/services/ai_service.py`, `V013__ai_clarify_sessions.sql` | Sticky in-memory only when env forces memory |
| **BE-023** | `GET /scan/{scan_id}` (auth) | `api/routers/scan.py`, `api/services/scan_service.py` | Scan ownership column not added |
| **BE-010** | Calendar month helpers for seek/warmup; meta notes; fetcher 30d labeled approx-only | `api/services/timeframes.py`, `api/schemas/meta.py`, `data/fetcher.py`, tests | Exchange fetch still uses approx 30d ms (documented) |

### Wave 4

| ID | What was done | Files touched | Deferred |
|----|---------------|---------------|----------|
| **BE-021** | FK/CHECK/unique-open index; merge overlapping detected gaps before insert; skip overlapping opens | `V014__data_gaps_constraints.sql`, `data/gaps.py` | Exclusion constraint for arbitrary overlaps not added (exact unique + app merge) |
| **BE-022** | CHECK constraints on replay/backtest/scan status|state | `V015__status_check_constraints.sql` | Shared Python enum module not extracted |

---

## FE coordination notes (for Agent H)

- Bootstrap: use `GET /auth/me` (or `/users/me`) with Bearer — public `GET /users/{id}` is gone.
- Auth UX: claim + passwordless create removed; register/login only.
- Chart-data empty windows: `empty: true` + empty candles — do not treat as historical prior chunk.
- Backtest: stop sending `user_id`; send JWT.
- Replay/live WS: `?token=<jwt>` (or Authorization header).
- Scan/AI/backtest: require JWT.

---

## Gaps / closest-approach notes

1. **No Redis / shared limiter** — in-process RPM + WS slot caps (BE-004 recommended A).
2. **No email infra** — claim removed rather than proof-of-email (BE-002 A).
3. **DB migrations V011–V015** require a running Postgres to apply; not executed in this session (migrator ready).
4. **BE-001 live DB integration test** not added; commit path covered by repository change + mocked API tests.
5. **Derived metadata** (`SELECT_DERIVED_MAX_TS` etc.) not fully rewritten with incomplete-bucket filter; range reads + live poll path use filtered derived SELECT.

---

## Migrations added

| Version | Purpose |
|---------|---------|
| V011 | Replay session `user_id` |
| V012 | One default watchlist / email lower unique |
| V013 | AI clarify sessions |
| V014 | `data_gaps` constraints |
| V015 | Status/state CHECKs |
