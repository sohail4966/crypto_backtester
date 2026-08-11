# Agent F2 — Backend Remediation (Pass 2)

**Date:** 2026-08-11  
**Source:** `G_CODE_REVIEW.md` (G-001, G-002 BE half, G-004…G-009, G-011, G-012)  
**Scope:** Backend only (`backend/` + this report). No commit/push.

---

## Test results

```text
cd backend && APP_ENV=dev AI_CLARIFY_STORE=memory \
  .venv/bin/python -m pytest tests/api/ tests/ai/ -q
# → 113 passed
```

Targeted suites also green: settings, auth, scan, backtest, chart_data, live_ws, replay_ws, replay_service, candle_repository.

---

## Per-finding summary

| ID | Severity | Fix | Files |
|----|----------|-----|-------|
| **G-001** | Critical | Missing `APP_ENV`/`ENV` defaults to **prod** (fail-closed). Insecure JWT default only when explicit `APP_ENV=dev\|local`. | `api/settings.py`, `.env.example`, `tests/api/test_settings.py` |
| **G-002** | Critical (BE) | Distinct replay WS close codes: **4401=UNAUTHORIZED**, **4402=SUPERSEDED**, 4404=NOT_FOUND. | `api/ws/replay.py` |
| **G-004** | Important | Ownership (404 on mismatch) for `GET /backtest/{id}`, trades, `GET /scan/{id}`; chart-data `runId` requires JWT + ownership. Scan `user_id` via V016. | routers/services/repos, `V016__scan_run_owner.sql`, tests |
| **G-005** | Important | V012 rewritten: collision dedupe (`lower(email)+dupN`) before unique index. Safe — V012 not yet applied to prod. | `V012__watchlist_default_and_email.sql` |
| **G-006** | Important | `CORS_ORIGINS` localhost default only in explicit dev; required outside (validate at startup). Explicit empty string → `[]`. | `api/settings.py`, `.env.example`, tests |
| **G-007** | Important | V011 now `DELETE` orphans then `ALTER … SET NOT NULL` on `replay_sessions.user_id`. | `V011__replay_session_owner.sql` |
| **G-008** | Important | Register conflict → `REGISTRATION_FAILED` (not `EMAIL_EXISTS`). User create same; email update → `UPDATE_FAILED`. | `auth_service.py`, `user_service.py`, `test_auth.py` |
| **G-009** | Important | Live WS groups by TF; `1m` uses `WHERE symbol = ANY(%)` + `DISTINCT ON`. Derived TFs still per-symbol on shared conn. | `live.py`, candle service/repo, `data/repository/queries.py` |
| **G-011** | Minor | `UserRepository.create` hard-raises; use `create_with_password`. | `user_repository.py`, test |
| **G-012** | Minor | Scan insert commit unit test; ownership tests for get backtest/scan/chart overlays. | `test_scan.py`, `test_backtest.py` |

FE-owned (not done here): **G-003**, **G-010**, FE half of **G-002**.

---

## FE coordination — replay WS close codes (G-002)

Update `frontend/src/constants/replay.ts` and `useReplayWs.ts`:

| Code | Constant | Meaning | FE action |
|------|----------|---------|-----------|
| **4401** | `REPLAY_CLOSE_UNAUTHORIZED` | Missing/invalid JWT | `notifyAuthFailure` + clear queue / AuthGate |
| **4402** | `REPLAY_CLOSE_SUPERSEDED` | Same session opened in another tab | Amber “opened in another tab”; **keep** auth |
| **4404** | (existing) | Session not found / not owned | Existing not-found path |

Do **not** map 4401 → superseded. Prior FE constant `REPLAY_CLOSE_SUPERSEDED = 4401` must become **4402**.

Chart-data: when requesting overlays with `runId`, send Bearer JWT (401 without; 404 if not owner). Plain candle windows remain public.

---

## Migrations

| Version | Change |
|---------|--------|
| V011 | Replay `user_id` + **NOT NULL** after orphan delete |
| V012 | Email lower unique + **collision dedupe** before index |
| V016 | **New** — `scan_runs.user_id` NOT NULL (+ orphan delete) |

Ops: set `APP_ENV=dev` locally; staging/prod must set strong `JWT_SECRET` and explicit `CORS_ORIGINS`.

---

## Gaps / notes

1. Derived-TF live batch still N queries (shared conn); `1m` is the primary live path and is batched.
2. Pre-V016 scan rows are deleted on migrate (unattributed).
3. Register uses `REGISTRATION_FAILED` (not `AUTH_FAILED`) to distinguish from login `INVALID_CREDENTIALS` while avoiding email enumeration.
