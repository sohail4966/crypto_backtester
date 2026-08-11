# Agent G3 — Code Review Pass 3 (Final Re-review)

**Date:** 2026-08-11  
**Base:** `3e81297ab10391e15992ad1ad3323d2a153a1d20`  
**Head:** working tree (uncommitted)  
**Sources:** `G2_CODE_REVIEW.md`, `G2_REMEDIATION.md`, `F2_BACKEND_REMEDIATION.md`, `H2_FRONTEND_REMEDIATION.md`  
**Scope:** Re-verify G2-001..G2-005; confirm no Critical/Important regressions from the full hardening effort; spot-check security contracts.

---

## Verdict

**READY**

All G2 findings are fixed in the working tree. Prior Critical/Important items from G1/G2 remain closed. Focused BE + FE tests are green. No new Critical, Important, or actionable Minor defects found.

---

## G2 disposition (G2-001..G2-005)

| ID | Prior sev | Status | Evidence |
|----|-----------|--------|----------|
| **G2-001** | Important | **Fixed** | `obtainDevToken` falls through to login on `REGISTRATION_FAILED` \| `EMAIL_EXISTS` \| `AUTH_FAILED`. Unit tests cover both `REGISTRATION_FAILED` and legacy `EMAIL_EXISTS`. |
| **G2-002** | Minor | **Fixed** | `V017__backtest_run_owner_not_null.sql` deletes null owners then `ALTER … SET NOT NULL`. |
| **G2-003** | Minor | **Fixed** | BE `test_replay_ws_close_codes_auth_vs_superseded_are_distinct` (4401≠4402 + handler uses `WS_SUPERSEDED`); `test_chart_data_run_id_ownership_mismatch_404`; ops note in `G2_REMEDIATION.md` for draft V011/V012 DBs. |
| **G2-004** | Minor | **Fixed** | OpenAPI has no `/auth/claim` / `AuthClaimRequest`; bearer description points at register/login only. |
| **G2-005** | Minor | **Fixed** | `.env.example` notes redacting `token=` / Authorization in access logs. |

---

## Spot-checks (requested)

| Check | Result |
|-------|--------|
| `REGISTRATION_FAILED` in `obtainDevToken` | **OK** — login fallback + test |
| V017 backtest `user_id NOT NULL` | **OK** — migration present |
| OpenAPI no `/auth/claim` | **OK** — zero matches |
| WS 4401 / 4402 tests | **OK** — constants + handler source assert; FE `replayWsClient` maps both |
| Chart non-owner `runId` → 404 | **OK** — `test_chart_data_run_id_ownership_mismatch_404` |
| `.env.example` token redact note | **OK** — G-014 / G2-005 comment |

---

## Prior Critical / Important (G-001..G-009) — still closed

| ID | Status | Brief evidence |
|----|--------|----------------|
| **G-001** | Closed | `app_env()` missing/unknown → `prod`; forgeable JWT only in explicit `dev`/`local`; `validate_security_settings()` at startup |
| **G-002** | Closed | BE `WS_UNAUTHORIZED=4401`, `WS_SUPERSEDED=4402`; FE constants + `useReplayWs` (`notifyAuthFailure` on 4401, amber superseded on 4402) |
| **G-003** | Closed | `prefetchPriorChunk` uses `hasCoverage` + `isRangedFallbackResponse` / empty → `reachedEarliestRef` |
| **G-004** | Closed | Backtest/scan GET ownership 404; chart `runId` JWT + ownership via `get_chart_overlays` |
| **G-005** | Closed | V012 `+dupN` collision rename then `uq_users_email_lower` |
| **G-006** | Closed | `CORS_ORIGINS` required outside explicit dev/local |
| **G-007** | Closed | V011 orphan delete + `replay_sessions.user_id NOT NULL` |
| **G-008** | Closed | Register → `REGISTRATION_FAILED`; FE DEV bootstrap aligned (G2-001) |
| **G-009** | Closed | Live WS groups by TF; `1m` batched with `ANY(%)` (derived TF residual accepted) |

Minors G-010..G-013 remain fixed; G-014 remains the documented ops residual (redact note shipped).

---

## Tests run (this pass)

```text
# Backend — 52 passed
cd backend && APP_ENV=dev AI_CLARIFY_STORE=memory \
  .venv/bin/python -m pytest \
  tests/api/test_auth.py tests/api/test_settings.py \
  tests/api/test_scan.py tests/api/test_backtest.py \
  tests/api/test_chart_data.py tests/api/test_replay_ws.py -q

# Frontend — 25 passed
cd frontend && npm test -- --run \
  src/hooks/useChunkManager.test.tsx \
  src/services/replayWsClient.test.ts \
  src/services/userBootstrap.test.ts \
  src/utils/chartDataWindow.test.ts \
  src/services/api.test.ts
```

---

## What was done well

- Fail-closed env/JWT/CORS is coherent end-to-end with tests and `.env.example` guidance.
- Replay auth vs superseded close codes are aligned on BE and FE, including distinct UX paths.
- Ownership IDOR hardening is consistent across backtest, scan, and chart overlays.
- FE/BE register anti-enum contract is closed (`REGISTRATION_FAILED` + DEV login fallback).
- Schema parity: replay, scan, and backtest owners are all `NOT NULL` after migrations.

---

## Production readiness checklist

1. ~~G-001 / G-006 fail-closed~~ **Done**
2. ~~G-002 distinct WS codes~~ **Done**
3. ~~G-003 FE-010/011 wire-up~~ **Done**
4. ~~G-004 ownership~~ **Done**
5. ~~G-005 V012 dedupe~~ **Done**
6. ~~G2-001 REGISTRATION_FAILED bootstrap~~ **Done**
7. ~~G2-002..G2-005 polish~~ **Done**

Ops reminders (not defects): set strong `JWT_SECRET` + explicit `CORS_ORIGINS` outside `dev`/`local`; redact WS `?token=` in access logs; if a shared DB applied draft V011/V012 without the rewritten body, reset or hand-apply equivalents (see `G2_REMEDIATION.md`).

---

## Remaining issues

**NONE — no issues left.**

---

## Suggested next pipeline step

Hardening review loop is closed. Proceed to commit / PR / deploy prep as desired; no further Agent G pass required unless new changes land.
