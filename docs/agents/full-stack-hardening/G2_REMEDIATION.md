# G2 Remediation (pass 3 polish)

**Date:** 2026-08-11  
**Source:** `G2_CODE_REVIEW.md` (READY_WITH_NITS)

| ID | Status | Change |
|----|--------|--------|
| **G2-001** | Fixed | `obtainDevToken` treats `REGISTRATION_FAILED` (+ legacy `EMAIL_EXISTS`) as login fallback; unit tests updated |
| **G2-002** | Fixed | `V017__backtest_run_owner_not_null.sql` — delete null owners, `SET NOT NULL` |
| **G2-003** | Fixed | Replay WS close-code regression test (4401≠4402 + handler uses `WS_SUPERSEDED`); chart-data non-owner `runId` 404 test; ops note: if draft V011/V012 already applied on a shared DB, reset schema or hand-apply V017-equivalent |
| **G2-004** | Fixed | Removed `/auth/claim` + `AuthClaimRequest` from OpenAPI; tags/bearer description updated |
| **G2-005** | Fixed | `.env.example` notes to redact `token=` / Authorization in access logs |

**Verify:** frontend `userBootstrap.test.ts` 9 passed; backend ownership + close-code + auth/settings tests green.
