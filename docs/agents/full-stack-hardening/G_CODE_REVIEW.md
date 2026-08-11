# Agent G — Code Review (Full-Stack Hardening)

**Date:** 2026-08-11  
**Base:** `3e81297ab10391e15992ad1ad3323d2a153a1d20`  
**Head:** working tree (uncommitted)  
**Sources:** `D_BACKEND_SOLUTIONS.md`, `E_FRONTEND_SOLUTIONS.md`, `C_SEVERITY_DEPENDENCY.md`, `F_BACKEND_IMPLEMENTATION.md`, `H_FRONTEND_IMPLEMENTATION.md`  
**Scope:** BE-001..BE-024 and FE-001..FE-018 recommended tracks vs actual code.

---

## Verdict

**NOT_READY**

Wave 1 auth hardening and most BE recommended fixes are present and largely correctly shaped (`/auth/me`, claim removed, JWT fail-closed *when* `APP_ENV` is non-dev, scan commit, chart `empty`, SQL `LIMIT`, replay ownership, caps, migrations V011–V015). Several **claimed-complete** FE chart fixes are **not wired**, replay WS close codes collide with auth failures, and a few multi-user / deploy footguns remain. Do not treat this working tree as production-ready until the Critical/Important items below are fixed and re-reviewed.

---

## What was verified (claims hold)

| Claim | Status | Evidence |
|-------|--------|----------|
| `GET /auth/me` exists | **OK** | `backend/api/routers/auth.py` |
| `/auth/claim` removed | **OK** | Auth router only register/login/me |
| Passwordless `POST /users` disabled | **OK** | `UserCreate.password` required |
| FE bootstrap uses `/auth/me` | **OK** | `getCurrentUser()` → `/auth/me` |
| FE parses `{ error: { code, message } }` | **OK** | `formatErrorMessage` / `ApiError.code` |
| Scan `conn.commit()` | **OK** | `ScanRepository.insert` |
| Chart empty window `empty: true`, no latest fallback | **OK** | `chart_data_service` + test |
| Backtest body `user_id` removed; JWT attribution | **OK** | schema + router |
| Replay/live WS `?token=` | **OK** | BE `resolve_ws_token`; FE `appendToken` |
| Replay ownership on REST/WS | **OK** | `user_id` on insert + `require_session` |
| CORS localhost regex default off outside dev | **OK** *(conditional)* | gated on `is_dev_env()` — see G-001 |
| Migrations advisory lock | **OK** | `pg_advisory_lock` in `migrator.py` |
| FE AuthGate / AuthModal for non-dev | **OK** | `allowDevAuth()` + `AuthGate` |
| ReplayRoot always mounted | **OK** | `AppShell` wraps `ReplayRoot` |
| Replay outbound command queue | **OK** | `ReplayWsClient` coalesce/flush |
| Timestamptz windows for backtest/scan | **OK** | `_unix_to_iso` full ISO |

Targeted BE tests run during review: `test_auth`, `test_settings`, `test_chart_data`, `test_scan` → **18 passed**.

---

## Findings

### Critical

#### G-001 — `APP_ENV` defaults to `dev`, undermining BE-003 / BE-017 fail-closed
**Files:** `backend/api/settings.py` (`app_env()`, `jwt_secret()`, `cors_allow_localhost_regex()`)

If a shared/prod deploy sets neither `APP_ENV`/`ENV` nor a strong `JWT_SECRET`, the process **starts with the forgeable default JWT secret** and **enables localhost CORS regex**. Recommended BE-003 assumes non-dev fail-closed; the default environment is still `dev`, so misconfigured “prod-looking” hosts stay open.

**Fix:** Default unknown/missing env to fail-closed (`prod` or require explicit `APP_ENV`), or refuse start when `JWT_SECRET` is unset regardless of env (keep a single `APP_ENV=dev` opt-in for the local default). Document and assert in deploy/CI.

#### G-002 — Replay WS close code `4401` means both UNAUTHORIZED and SUPERSEDED
**Files:** `backend/api/ws/replay.py` (`WS_UNAUTHORIZED = 4401`, superseded `prior.close(code=4401)`); `frontend/src/constants/replay.ts` (`REPLAY_CLOSE_SUPERSEDED = 4401`); `frontend/src/hooks/useReplayWs.ts`

Auth failure and tab-supersede share **4401**. FE maps 4401 → “Opened in another tab” / amber superseded path — **not** session clear / re-auth (FE-003). Expired/missing tokens on replay WS are misclassified; users keep a broken “playing” mental model instead of AuthGate recovery.

**Fix:** Distinct codes (e.g. `4401` auth, `4402` superseded — or vice versa); FE maps auth close → `notifyAuthFailure` + queue clear.

---

### Important

#### G-003 — FE-010 / FE-011 claimed done but not wired into `useChunkManager`
**Files:** `frontend/src/hooks/useChunkManager.ts`; helpers exist in `chunkManager.hasCoverage`, `utils/chartDataWindow.isRangedFallbackResponse`

H report marks FE-010/FE-011 **Done**. Prefetch still:
1. Guards with `hasChunk(priorStart)` (request key), **not** `hasCoverage(priorStart, priorEnd)`.
2. Always `addChunk(data.start, …)` with **no** `isRangedFallbackResponse` check / `reachedEarliest` handling.

Empty BE responses are partially mitigated (`ChunkManager.addChunk` no-ops on empty candles), so current BE empty contract reduces corruption risk — but **request/response key thrash (FE-010) remains**, and the defensive FE-011 path is dead code outside unit tests.

**Fix:** In `prefetchPriorChunk`, use `hasCoverage`; on fallback/empty, skip ingest and mark earliest exhausted; add an integration-style hook/chunk test that fails if wiring regresses.

#### G-004 — IDOR on authenticated (and chart) retrieve paths
**Files:** `backend/api/routers/backtest.py` (`GET /{run_id}`, trades); `backend/api/routers/scan.py` (`GET /{scan_id}`); `backend/api/services/chart_data_service.py` (`run_id` overlays); chart-data router still **unauthenticated**

Any JWT (or no JWT for chart-data) can fetch another user’s backtest/scan payload or strategy overlays by UUID. BE-005/BE-006 ownership patterns were not extended to retrieve/overlays; BE-023 explicitly deferred scan ownership.

**Fix:** Enforce `user_id` ownership (404 on mismatch) for backtest/scan get; require auth + ownership for chart-data overlays when `runId` is set (or strip overlays for non-owners).

#### G-005 — V012 email migration can fail on case-variant collisions
**Files:** `backend/data/migrations/sql/V012__watchlist_default_and_email.sql`

Comment promises `+dupN` collision resolution; SQL only `UPDATE … SET email = lower(email)` then creates `uq_users_email_lower`. Existing `Alice@x` + `alice@x` rows will break the UPDATE (unique) or index create and **block API startup migrations**.

**Fix:** Dedupe/rename colliding lowers before unique index; add a dry-run/ops note in F gaps.

#### G-006 — `CORS_ORIGINS` still defaults to localhost even when `APP_ENV=prod`
**Files:** `backend/api/settings.py` `cors_origins()`

BE-017 recommended fail-closed localhost **regex**; the static allowlist still defaults to `http://localhost:5173,3000` unless overridden. Prod with credentials + forgotten `CORS_ORIGINS` still allows local origins.

**Fix:** Empty/default allowlist outside dev; require explicit origins in staging/prod (mirror JWT fail-closed).

#### G-007 — Replay `user_id` never forced `NOT NULL` after V011
**Files:** `backend/data/migrations/sql/V011__replay_session_owner.sql`

Column added nullable; orphans deleted; app insert always sets owner — but DB still allows `NULL` user_id if any code path regresses. Recommended sketch: nullable briefly then NOT NULL.

**Fix:** Follow-up migration `ALTER … SET NOT NULL` (after confirming no nulls).

#### G-008 — Register still returns `EMAIL_EXISTS` (BE-024 incomplete)
**Files:** `backend/api/services/auth_service.py`, `user_service.py`

Message is generic; **code** still distinguishes existence. Patient clients enumerate via code. Login is correctly uniform (`INVALID_CREDENTIALS`).

**Fix:** Uniform `AUTH_FAILED` / `REGISTRATION_FAILED` code (or always-200 anti-enum product choice).

#### G-009 — Live WS “batch” is shared-conn N queries, not one multi-symbol SQL
**Files:** `backend/api/ws/live.py` `_latest_bars`

BE-019 recommended shared conn **and** `WHERE symbol = ANY(%)`. Shared conn landed; per-symbol poll loop remains. Acceptable interim but incomplete before enabling `VITE_LIVE_WS` at scale.

---

### Minor

#### G-010 — FE still ships `/auth/claim` and passwordless `createUser` helpers
**Files:** `frontend/src/services/userBootstrap.ts`

Claim is DEV-fallback only after BE removed the route (always fails in prod builds with `allowDevAuth` false). `createUser` posts without password → 422. Dead/misleading surface; remove or hard-delete from bundles.

#### G-011 — Passwordless `UserRepository.create` remains
**Files:** `backend/api/repositories/user_repository.py`

HTTP path blocks it; legacy method still inserts null-hash users if called. Prefer delete or raise.

#### G-012 — Scan/AI ownership & retrieve tests thin; no live DB persist assertion
As noted in F: BE-001 commit is code-correct; no integration test proves row survives request-scoped connection. Scan GET has no owner tests (ties to G-004).

#### G-013 — FE-007 chart canvas markers still deferred
Equity sparkline + query flags exist; full chart markers not drawn. Matches H deferred note — product gap, not a security hole.

#### G-014 — WS JWT in query string
Agreed contract with BE-004/006; be aware of access-log leakage (ops: redact `token=`).

---

## Plan alignment summary

| Area | Alignment |
|------|-----------|
| BE Wave 1 (003/002/024/016/001/004/008/007/017) | **Mostly complete**; G-001/G-006/G-008 weaken 003/017/024 |
| BE Wave 2 (005/006/011/009) | **Complete** in app logic; G-007 schema harden leftover |
| BE Wave 3–4 | **Largely complete**; AI Postgres store OK; live batch partial (G-009); V012 risk (G-005) |
| FE Wave 1 (001–004) | **Complete** for contracts; claim helper leftover (G-010) |
| FE Wave 2 (009/008/011/010) | **008/009 OK**; **010/011 incomplete (G-003)**; WS auth close (G-002) |
| FE Wave 3–4 | Largely present (legend, sync, drawings, indicators persist/per-pane, watchlist CRUD, TF extras, clients-only scan/AI, live behind flag) |

Deviations that are **acceptable:** in-process rate limits (no Redis); claim removed vs email-proof; FE-006 clients-only; FE-005 flag-gated; FE-016 static TF list without `1M`.

Deviations that are **problematic:** G-001–G-008 above (especially G-002/G-003 vs H “Done” claims).

---

## Production readiness checklist (blockers)

1. Fix G-001 (env/JWT fail-closed) and G-006 (CORS origins default).
2. Fix G-002 (distinct WS close codes + FE auth recovery).
3. Wire G-003 (FE-010/011 into prefetch path) and add a regression test that would have failed this review.
4. Address G-004 (ownership on retrieve/overlays) before multi-tenant prod.
5. Harden G-005 (V012 collision dedupe) before applying migrations on any DB with mixed-case emails.
6. Re-run Agent A/B style issue pass on remaining items; then Agent G re-review.

---

## Remaining issues for next A/B loop

| ID | Sev | Title | Suggested owner |
|----|-----|-------|-----------------|
| G-001 | Critical | APP_ENV default `dev` allows forgeable JWT + localhost CORS | F |
| G-002 | Critical | Replay WS `4401` auth vs superseded collision | F + H |
| G-003 | Important | FE-010/011 helpers unused in `useChunkManager` | H |
| G-004 | Important | Backtest/scan/chart overlay IDOR | F |
| G-005 | Important | V012 email lower collision can fail migrate | F |
| G-006 | Important | `CORS_ORIGINS` localhost default in prod | F |
| G-007 | Important | Replay `user_id` should be `NOT NULL` | F |
| G-008 | Important | Register `EMAIL_EXISTS` code enumerates | F |
| G-009 | Important | Live WS multi-symbol batch query | F |
| G-010 | Minor | Remove FE claim/passwordless create helpers | H |
| G-011 | Minor | Remove passwordless `UserRepository.create` | F |
| G-012 | Minor | Live DB scan persist + ownership tests | F |
| G-013 | Minor | FE-007 chart markers UI | H |
| G-014 | Minor | Redact WS `token` query in logs | Ops/F |

---

## Suggested next pipeline step

Feed **G-001..G-009** into a focused remediation wave (F+H), then re-run verification (pytest auth/replay/chart + frontend chunk/replay WS tests) before another Agent G pass. Only then consider `READY_WITH_NITS` or `READY`.
