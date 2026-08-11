# Agent G2 — Code Review Pass 2 (Re-review)

**Date:** 2026-08-11  
**Base:** `3e81297ab10391e15992ad1ad3323d2a153a1d20`  
**Head:** working tree (uncommitted)  
**Sources:** `G_CODE_REVIEW.md`, `F2_BACKEND_REMEDIATION.md`, `H2_FRONTEND_REMEDIATION.md`  
**Scope:** Re-verify G-001..G-014; hunt remediation regressions; spot-check security contracts.

---

## Verdict

**READY_WITH_NITS**

All prior **Critical** findings (G-001, G-002) and the production security / ownership Important set (G-003..G-008 BE, G-004, G-005, G-006, G-007) are fixed in the working tree and FE+BE aligned on replay WS codes. Focused tests are green.

One **Important** remediation coordination gap remains: DEV silent bootstrap still keys off obsolete `EMAIL_EXISTS` / `AUTH_FAILED` and will not fall through to login on `REGISTRATION_FAILED` (G-008’s new code). That does **not** reopen email enumeration (BE is correct) and does **not** break production `AuthModal` (user can switch to login), but it is a real FE/BE contract miss that should be fixed before calling the hardening loop closed.

No new Criticals found.

---

## Prior findings disposition (G-001..G-014)

| ID | Prior sev | Status | Evidence |
|----|-----------|--------|----------|
| **G-001** | Critical | **Fixed** | `app_env()` defaults missing/unknown → `prod`; `jwt_secret()` forgeable default only in explicit `dev`/`local`; `validate_security_settings()` in `main.py` lifespan. Tests in `test_settings.py`. |
| **G-002** | Critical | **Fixed** | BE: `WS_UNAUTHORIZED=4401`, `WS_SUPERSEDED=4402` (`api/ws/replay.py`). FE: constants + `closeKind` + `useReplayWs` → `notifyAuthFailure` on 4401, amber superseded on 4402. |
| **G-003** | Important | **Fixed** | `prefetchPriorChunk` uses `hasCoverage`; `isRangedFallbackResponse` / empty → `reachedEarliestRef`; regression tests in `useChunkManager.test.tsx`. |
| **G-004** | Important | **Fixed** | Backtest GET/trades + scan GET ownership → 404; chart-data `runId` requires JWT + `get_chart_overlays` ownership; V016 `scan_runs.user_id NOT NULL`. |
| **G-005** | Important | **Fixed** | V012 ranks `lower(email)`, renames `rn>1` to `email_lower\|\|'+dup'\|\|rn`, then unique index. |
| **G-006** | Important | **Fixed** | `cors_origins()` localhost default only in `is_dev_env()`; otherwise requires `CORS_ORIGINS` (empty string → `[]`). |
| **G-007** | Important | **Fixed** | V011 deletes null owners then `ALTER … SET NOT NULL`. *(Ops: if a draft V011 without NOT NULL was already applied locally, rewrite will not re-run — see G2-003.)* |
| **G-008** | Important | **Fixed (BE)** | Register conflict → `REGISTRATION_FAILED`; no `EMAIL_EXISTS` in API response. FE DEV bootstrap not updated → **G2-001**. |
| **G-009** | Important | **Fixed (primary path)** | Live WS groups by TF; `1m` uses `WHERE symbol = ANY(%)` + `DISTINCT ON`. Derived TFs still N queries on shared conn (accepted residual). |
| **G-010** | Minor | **Fixed** | `claimUser` / passwordless `createUser` removed; `AUTH_EXEMPT_PREFIXES` is login/register only. |
| **G-011** | Minor | **Fixed** | `UserRepository.create` hard-raises; use `create_with_password`. |
| **G-012** | Minor | **Fixed** | Scan insert `user_id` assertion; ownership tests for backtest/scan get; chart runId auth/404 tests. |
| **G-013** | Minor | **Fixed** | Minimal `BacktestMarkers` + overlay store path shipped. |
| **G-014** | Minor | **Accepted residual** | WS JWT still in `?token=` by design; ops should redact access logs. |

---

## Contract spot-checks

| Contract | Result |
|----------|--------|
| `APP_ENV` fail-closed | **OK** — missing → `prod`; JWT + CORS validated at startup |
| JWT non-dev | **OK** — required, min 32 chars, rejects known placeholders |
| `CORS_ORIGINS` | **OK** — no localhost default outside explicit `dev`/`local` |
| Replay WS 4401 / 4402 | **OK** — BE+FE constants and handlers aligned |
| Ownership backtest/scan/chart `runId` | **OK** — JWT + owner match; public candles without `runId` |
| FE prefetch `hasCoverage` + empty guard | **OK** — wired + tested |
| Register `REGISTRATION_FAILED` | **OK (BE)** / **FE DEV gap** — see G2-001 |

---

## Tests run (this pass)

```text
# Backend
cd backend && APP_ENV=dev AI_CLARIFY_STORE=memory \
  .venv/bin/python -m pytest \
  tests/api/test_auth.py tests/api/test_settings.py \
  tests/api/test_scan.py tests/api/test_backtest.py \
  tests/api/test_chart_data.py tests/api/test_replay_ws.py -q
# → 50 passed

# Frontend
cd frontend && npm test -- --run \
  src/hooks/useChunkManager.test.tsx \
  src/services/replayWsClient.test.ts \
  src/services/userBootstrap.test.ts \
  src/utils/chartDataWindow.test.ts
# → 19 passed
```

Note: `userBootstrap.test.ts` still mocks `EMAIL_EXISTS` and therefore does **not** catch G2-001.

---

## New / remaining findings

### Important

#### G2-001 — DEV bootstrap ignores `REGISTRATION_FAILED` after G-008
**Files:** `frontend/src/services/userBootstrap.ts` (`obtainDevToken`); `frontend/src/services/userBootstrap.test.ts`

G-008 changed duplicate-register from `EMAIL_EXISTS` → `REGISTRATION_FAILED`. `obtainDevToken` still only treats `EMAIL_EXISTS` \| `AUTH_FAILED` as “fall through to login”:

```117:120:frontend/src/services/userBootstrap.ts
    if (code === 'EMAIL_EXISTS' || code === 'AUTH_FAILED') {
      return storeAuthSession(await loginUser(DEV_USER_EMAIL, DEV_USER_PASSWORD))
    }
    throw error
```

**Impact:** With `allowDevAuth()`, second+ app loads (or any load after `dev@local` already exists) fail silent bootstrap instead of logging in. Production `AuthModal` is unaffected (shows message; user can switch to login).

**Fix:** Treat `REGISTRATION_FAILED` (and keep legacy `EMAIL_EXISTS` if desired) as login fallback; update the unit test to assert the new code.

---

### Minor

#### G2-002 — `backtest_runs.user_id` still nullable
**Files:** `backend/data/migrations/sql/V008__backtest_runs.sql` (`REFERENCES … ON DELETE SET NULL`)

Replay (V011) and scan (V016) are `NOT NULL`. Backtest ownership is enforced in app code (null owner → 404), but DB still allows null if a code path regresses. Optional follow-up: migrate orphans + `SET NOT NULL` for parity.

#### G2-003 — Migration rewrite / test gaps
1. **V011/V012 rewritten in place.** Correct for fresh DBs; any environment that already recorded draft versions without NOT NULL / dedupe will not re-apply. Prefer a new V017 if any shared DB applied drafts, or document reset.
2. **No BE test** asserts superseded close uses **4402** (FE unit test covers mapping only).
3. **No chart-data test** for authenticated non-owner `runId` (logic shares `get_chart_overlays` ownership check; backtest GET mismatch is covered).

#### G2-004 — Docs/OpenAPI still mention `/auth/claim`
**Files:** `backend/docs/openapi.yaml`, assorted phase docs  

Route is gone; OpenAPI still documents claim. Docs drift only — not runtime.

#### G2-005 — WS `token=` query logging (ex-G-014)
Unchanged accepted residual; redact in reverse proxies / access logs.

---

## What was done well

- Fail-closed env/JWT/CORS is coherent (`validate_security_settings` at factory + lifespan) with clear `.env.example` guidance.
- Replay auth vs superseded close codes are consistently named and handled on both sides.
- IDOR hardening on retrieve paths is real (404 on mismatch), including chart overlays when `runId` is set.
- FE-010/011 are actually wired into the prefetch path with tests that would fail on regression.
- V012 collision handling matches the earlier promised `+dupN` behavior.

---

## Plan alignment (post-remediation)

| Area | Alignment |
|------|-----------|
| BE Wave 1 fail-closed / auth | **Complete** |
| Replay WS codes | **Complete** (FE+BE) |
| Ownership retrieve / overlays | **Complete** (app); backtest schema NOT NULL optional |
| FE chunk prefetch | **Complete** |
| Register anti-enum | **BE complete**; FE DEV bootstrap one-liner missing |
| Live batch | **1m complete**; derived TF interim OK |

---

## Production readiness checklist

1. ~~G-001 / G-006 fail-closed~~ **Done**
2. ~~G-002 distinct WS codes~~ **Done**
3. ~~G-003 FE-010/011 wire-up~~ **Done**
4. ~~G-004 ownership~~ **Done**
5. ~~G-005 V012 dedupe~~ **Done**
6. Fix **G2-001** (accept `REGISTRATION_FAILED` in `obtainDevToken` + test) before treating the hardening loop as fully closed.
7. Optional: G2-002 / G2-003 polish.

---

## Remaining issues for next loop

| ID | Sev | Title | Suggested owner |
|----|-----|-------|-----------------|
| G2-001 | Important | DEV bootstrap: handle `REGISTRATION_FAILED` → login | H |
| G2-002 | Minor | `backtest_runs.user_id` NOT NULL migration | F |
| G2-003 | Minor | V011/V012 rewrite ops note; BE 4402 + chart non-owner tests | F |
| G2-004 | Minor | Remove `/auth/claim` from OpenAPI/docs | F |
| G2-005 | Minor | Redact WS `token=` in access logs | Ops |

Or state after G2-001: remaining are nits only → next G pass should be **READY**.

---

## Suggested next pipeline step

One-line FE fix for **G2-001** (+ update `userBootstrap` test). Optionally add BE superseded-4402 assertion. Then Agent G pass 3 should be able to return **READY**.
