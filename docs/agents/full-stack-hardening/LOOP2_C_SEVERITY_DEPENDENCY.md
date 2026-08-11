# Agent C (Loop 2) — Severity, Effort & Dependency Graph

**Date:** 2026-08-11
**Inputs:** `LOOP2_A_BACKEND_ISSUES.md` (20 issues), `LOOP2_B_FRONTEND_ISSUES.md` (11 issues).
**Purpose:** Rank every open finding by severity, size, and cross-stack dependency so Agents D/E/F/H can execute in a deterministic order.

---

## Severity summary

| Severity  | Count | IDs                                                                                                 |
|-----------|------:|-----------------------------------------------------------------------------------------------------|
| Critical  |     1 | BE-L2-001                                                                                           |
| Important |    13 | BE-L2-002, -003, -004, -005, -006, -007, -009, -010 · FE-L2-001, -002, -003, -005, -006             |
| Minor     |    17 | BE-L2-008, -011, -012, -013, -014, -015, -016, -017, -018, -019, -020 · FE-L2-004, -007, -008, -009, -010, -011 |
| **Total** |  **31** |                                                                                                     |

### Severity overrides against Agent A/B hints

Only two hints are overridden; the rest of the ratings are accepted as reported.

| ID         | A/B hint  | C rating | Justification                                                                                                                                                                                                            |
|------------|-----------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| BE-L2-008  | Important | **Minor**    | Over-broad `UniqueViolation` catch surfaces the wrong error message *only* when a second unique index (default-watchlist, future indices) actually fires. Under the normal register path today (email uniqueness) the message is still correct. Fits the scale's "latent footgun not hit in default path".         |
| BE-L2-011  | Important | **Minor**    | Login timing side-channel is a classic "timing side-channels with limited impact" case per this loop's severity scale. Exploitable only for email enumeration (not credential theft), throttled by BE-L2-010 once addressed. Kept in-scope but not a fix-now blocker. |

No Critical-hint issues were downgraded. BE-L2-002 (WS DB poison) was considered for a Critical bump because it silently kills every live-WS session after one transient DB error, but the socket poison is bounded to that one connection and disconnect/reconnect recovers — leaving it at Important per "resource poison under normal use".

---

## Prioritized fix order (top 15 for parent)

Ordering rule: (a) prod-fail / data-loss first, (b) user-visible correctness next, (c) contract truth (OpenAPI) before FE contract fixes that depend on it, (d) hardening (rate-limit, WS-token) after correctness, (e) polish last.

| Rank | ID          | Severity  | Effort | Blocks / blocked-by                                                                                       |
|-----:|-------------|-----------|:------:|-----------------------------------------------------------------------------------------------------------|
|    1 | BE-L2-001   | Critical  |   S    | Blocks nothing (foundational). Must ship in the same migration cut as BE-L2-016.                          |
|    2 | BE-L2-007   | Important |   S    | Independent; unblocks logged-out `/chart-data` UX. Cross-checks stale-token path implicit in FE-L2-009.  |
|    3 | BE-L2-002   | Important |   S    | Independent. Pairs conceptually with FE-L2-001/-002 (both are live-WS correctness).                       |
|    4 | FE-L2-001   | Important |   S    | Blocked-by: none (BE already emits `bar`). Cross-links **BE-L2-005** doc alignment.                        |
|    5 | FE-L2-002   | Important |   S    | Blocked-by: none. Cross-links **BE-L2-004/-005** so FE authors code from an accurate spec.                 |
|    6 | BE-L2-005   | Important |   S    | Blocks FE-L2-001, FE-L2-002 (spec truth for live-WS auth + payload).                                       |
|    7 | BE-L2-004   | Important |   S    | Blocks FE-L2-007 & any FE close-code work generated from OpenAPI.                                          |
|    8 | BE-L2-003   | Important |   M    | Blocks FE-L2-005, FE-L2-006 (SDK-gen / typed clients). Contains BE-L2-004 & BE-L2-005 as sub-items — fix in one PR. |
|    9 | BE-L2-006   | Important |   S    | Blocks any consumer generating clients from OpenAPI; removes the `ReplaySessionCreate.user_id` echo.       |
|   10 | FE-L2-005   | Important |   M    | Blocked-by: BE-L2-003 (schema-of-record). Rebuild client from post-fix openapi.                            |
|   11 | FE-L2-006   | Important |   M    | Blocked-by: BE-L2-003. Same PR family as FE-L2-005.                                                        |
|   12 | BE-L2-010   | Important |   M    | Independent. Reduces DoS surface exposed by BE-L2-011.                                                     |
|   13 | BE-L2-009   | Important |   L    | Blocked-by: none, but naturally pairs with BE-L2-010 (share Redis-backed limiter).                         |
|   14 | FE-L2-003   | Important |   L    | Blocks / blocked-by: **needs a new BE endpoint** (short-lived WS ticket or `Sec-WebSocket-Protocol` bearer) — spawn a companion BE issue during fix.                     |
|   15 | FE-L2-004   | Minor     |   S    | Independent; kept in top 15 as a cheap UX win that removes a raw pydantic 422 during onboarding.           |

**Effort key:** S ≤ ½ day · M ≈ 1 day · L > 1 day / multi-file / cross-stack.

---

## Full per-issue matrix

Legend: **BL** = blocked-by · **B** = blocks · dependencies list only *other loop-2 IDs*, not general codebase pre-reqs.

### Critical

| ID         | Severity | Effort | BL | B                     | Rank | Area           |
|------------|----------|:------:|----|-----------------------|:----:|----------------|
| BE-L2-001  | Critical | S      | —  | BE-L2-016 (safety net) |  1   | db / migrations |

### Important — Must-fix-now

| ID         | Severity  | Effort | BL                | B                          | Rank | Area                |
|------------|-----------|:------:|-------------------|----------------------------|:----:|---------------------|
| BE-L2-002  | Important | S      | —                 | (live-WS reliability)      |  3   | ws / reliability    |
| BE-L2-003  | Important | M      | —                 | FE-L2-005, FE-L2-006       |  8   | api-contract        |
| BE-L2-004  | Important | S      | —                 | FE close-code map (FE-L2-007) |  7   | ws / api-contract   |
| BE-L2-005  | Important | S      | —                 | FE-L2-001, FE-L2-002       |  6   | ws / api-contract   |
| BE-L2-006  | Important | S      | —                 | FE-generated clients       |  9   | api / schemas       |
| BE-L2-007  | Important | S      | —                 | —                          |  2   | auth / api          |
| BE-L2-009  | Important | L      | —                 | (real ceiling for BE-L2-010) | 13   | reliability / security |
| BE-L2-010  | Important | M      | —                 | mitigates BE-L2-011 impact |  12  | security / DoS      |
| FE-L2-001  | Important | S      | BE-L2-005 (doc)    | —                          |  4   | ws / contract       |
| FE-L2-002  | Important | S      | BE-L2-005 (doc)    | —                          |  5   | ws / auth           |
| FE-L2-003  | Important | L      | **new BE ticket / subprotocol endpoint** | —      |  14  | security / auth     |
| FE-L2-005  | Important | M      | BE-L2-003         | —                          |  10  | api / contract      |
| FE-L2-006  | Important | M      | BE-L2-003         | —                          |  11  | api / contract      |

### Minor — Should-fix / Nice-to-fix

| ID         | Severity | Effort | BL         | B          | Rank | Area                    |
|------------|----------|:------:|------------|------------|:----:|-------------------------|
| FE-L2-004  | Minor    | S      | —          | —          |  15  | auth / UX               |
| BE-L2-008  | Minor    | S      | —          | —          |  16  | auth / data-integrity   |
| BE-L2-011  | Minor    | S      | BE-L2-010 (throttle)  | — |  17  | security / auth         |
| FE-L2-009  | Minor    | S      | —          | —          |  18  | auth / watchlist        |
| FE-L2-008  | Minor    | S      | —          | —          |  19  | ws / auth / replay      |
| BE-L2-012  | Minor    | S      | —          | —          |  20  | ws / reliability        |
| BE-L2-013  | Minor    | S      | —          | —          |  21  | ws / concurrency        |
| FE-L2-007  | Minor    | S      | BE-L2-004  | —          |  22  | ws / UX                 |
| FE-L2-010  | Minor    | S      | —          | —          |  23  | api / watchlist         |
| BE-L2-014  | Minor    | S      | —          | —          |  24  | reliability / observability |
| BE-L2-019  | Minor    | M      | —          | —          |  25  | api-contract            |
| FE-L2-011  | Minor    | S      | —          | —          |  26  | ws / auth (defense-in-depth) |
| BE-L2-016  | Minor    | S      | BE-L2-001  | —          |  27  | migrations / data-integrity |
| BE-L2-015  | Minor    | M      | —          | —          |  28  | data-integrity          |
| BE-L2-020  | Minor    | S      | —          | —          |  29  | migrations / reliability |
| BE-L2-017  | Minor    | S      | —          | groups w/ BE-L2-018 |  30 | security / api-contract |
| BE-L2-018  | Minor    | S      | BE-L2-017  | —          |  31  | api-contract            |

---

## Cross-stack link map (FE ↔ BE)

These pairs must be resolved together or fixed with awareness of the other side to avoid regressions.

| Theme                                    | Backend            | Frontend         | Notes |
|------------------------------------------|--------------------|------------------|-------|
| Live-WS payload contract                 | BE-L2-005          | **FE-L2-001**    | BE already emits `bar`; FE reads `candle`. Fix FE to `bar`, fix BE doc label same PR. |
| Live-WS close codes / auth-clear         | BE-L2-005          | **FE-L2-002**    | FE never surfaces `close.code` → misses 4401/4429. Fix FE + reword BE openapi. |
| Replay-WS close-code truth               | **BE-L2-004**      | FE-L2-007        | Spec still calls 4401 "superseded". FE derives close-code UX from spec authors' reading of BE; fix spec, then FE 4429 branch. |
| Auth on `scan`/`backtest`/`replay`/`ai`  | **BE-L2-003**      | FE-L2-005, FE-L2-006 | Missing `security:` blocks + wrong tag copy. FE client shapes were coded against stale wording — fix openapi first, regenerate types, then update clients. |
| Users listing / 410                      | BE-L2-003 (docs)   | —                | FE already avoids `GET /users` post-G2; keep doc alignment for external consumers. |
| WS bearer leakage                        | (new BE ticket)    | **FE-L2-003**    | FE half of G-014. Requires a **new BE endpoint** (short-lived ticket) or `Sec-WebSocket-Protocol` bearer support — Agent D/H must schedule the BE half. |
| Register password policy                 | `AuthRegisterRequest.min_length=8` | **FE-L2-004** | Cheap FE fix; consider extracting a shared constant surfaced in `.env` / typed enum. |
| Ownership 404 conventions                | BE-L2-017 (echo)   | —                | Informational — kept for D/F to acknowledge as intentional anti-enumeration. |
| Public `/chart-data`                     | **BE-L2-007**      | (implicit)       | FE-L2-009's post-clearing behaviour is safe once BE stops 401-ing optional paths on stale tokens. |
| Migration cut-in                         | BE-L2-001 + BE-L2-016 | —             | Ship BE-L2-001's FK fix and BE-L2-016's data-loss doc in the same V018 window (or add pre-flight archive step). |

---

## Grouping for Agents D/E/F/H

### 1. Must-fix-now (Critical + Important that break prod / correctness)

Break down by owner:

- **Agent D (BE, prod-fail / data-integrity)**
  - BE-L2-001 (rank 1) — new migration V018 fixing FK to `ON DELETE CASCADE` (or `RESTRICT`).
  - BE-L2-002 (rank 3) — WS DB conn: switch to `autocommit=True` on connect or add `rollback()` in the poll error path.
  - BE-L2-007 (rank 2) — `get_optional_user`: swallow `UnauthorizedError` when no `runId` present.

- **Agent D/E (BE, contract truth for openapi.yaml)**
  - BE-L2-003 (rank 8) — add `security: bearerAuth` to scan, backtest, replay, AI, `GET/PATCH/DELETE /users/{id}`; document 401/403; document `GET /users` 410; document `GET /scan/{id}`.
  - BE-L2-004 (rank 7) — replay-WS close-code prose to 4401=UNAUTHORIZED, 4402=SUPERSEDED, 4404=NOT_FOUND.
  - BE-L2-005 (rank 6) — remove "Public in v1" for `/ws/live`; document `?token=` and 4401/4429.
  - BE-L2-006 (rank 9) — drop `user_id` from `ReplaySessionCreate` schema (and OpenAPI component).

- **Agent F (FE)**
  - FE-L2-001 (rank 4) — read `row.bar`; drop the phantom `incomplete` gate.
  - FE-L2-002 (rank 5) — surface `close.code` in `LiveWsClient` handlers; wire 4401→`notifyAuthFailure`, 4429→toast, in `useLiveCandles`.
  - FE-L2-005 (rank 10), FE-L2-006 (rank 11) — rewrite `scanApi`/`aiApi` types + calls to match schemas *after* BE-L2-003 lands.

### 2. Should-fix (Important residual)

- **Agent D (BE, hardening)**
  - BE-L2-010 (rank 12) — add per-IP + per-account rate limit to `POST /auth/register` and `POST /users` (reuse or extend the AI-limiter dep).
  - BE-L2-009 (rank 13) — Redis (or shared-store) backed limiter; document `--workers` interaction; add cleanup for empty deques.

- **Agent H (FE + cross-stack security)**
  - FE-L2-003 (rank 14) — move JWT off `localStorage` (in-memory + `sessionStorage` fallback) *and* land a new BE `POST /ws/tickets` (short-lived, one-shot) so WS URLs stop carrying bearer tokens. Requires paired BE work — Agent D adds the endpoint alongside.

### 3. Nice-to-fix (Minor)

- **Agent E (BE polish + auth hardening)**
  - BE-L2-008 (rank 16) — narrow `UniqueViolation` catch by `exc.diag.constraint_name`.
  - BE-L2-011 (rank 17) — precomputed dummy bcrypt hash to normalize login timing.
  - BE-L2-012 (rank 20) — move `acquire_ws_slot` inside the outer `try/finally` (both replay & live).
  - BE-L2-013 (rank 21) — `asyncio.Lock` around `_active_connections` swap.
  - BE-L2-014 (rank 24) — `logger.exception` + counter on scan-persist error.
  - BE-L2-015 (rank 28) — `EXCLUDE USING gist` on `data_gaps` for `status='open'`.
  - BE-L2-016 (rank 27) — either archive orphan `backtest_runs` before delete or add a bright warning in V017's file + release notes. Land with BE-L2-001.
  - BE-L2-019 (rank 25) — deprecate or JWT-gate `POST /users`; align OpenAPI copy.
  - BE-L2-020 (rank 29) — advisory lock key = `hashtext(current_database())`.
  - BE-L2-017 / BE-L2-018 (rank 30/31) — drop the echoed `session_id` from the AI 404 message; grouped, single-line fix.

- **Agent F (FE polish)**
  - FE-L2-004 (rank 15) — password `minLength={mode==='register' ? 8 : 6}` (kept in top 15 because it's cheap and stops a visible pydantic 422).
  - FE-L2-007 (rank 22) — map 4429 → distinct "Too many concurrent connections" toast for both replay & live.
  - FE-L2-008 (rank 19) — reset `sessionId` + URL query on 4401 unauthorized branch of `useReplayWs`.
  - FE-L2-009 (rank 18) — reorder `WatchlistRoot` 401/403 handler so `notifyAuthFailure`'s `expired` reason is preserved (call `setNeedsAuth` without wiping `lastErrorCode`; or move the wipe behind an explicit "user changed" check).
  - FE-L2-010 (rank 23) — either drop unresolved IDs with a warning toast or fall back to `active_only=false`; keep partial rendering.
  - FE-L2-011 (rank 26) — `resolveReplayWsUrl` must assert same-origin (or accept only relative paths).

### 4. Deferred / accepted risk

None. Every item is in-scope. Two candidates were reviewed and rejected as "deferrable":

- BE-L2-017 (AI `SESSION_NOT_FOUND` echoes the caller-supplied ID) — *not deferred*: it's a 1-line fix even though the underlying 404 pattern is intentional. Grouped with BE-L2-018.
- BE-L2-020 (advisory lock key per-DB) — *not deferred*: single-line fix; keeping it in the Minor bucket rather than accepted-risk avoids ambiguity for future multi-DB deploys.

---

## Notes for downstream agents

- Land BE-L2-003, BE-L2-004, BE-L2-005, BE-L2-006 in a single "OpenAPI truthing" PR — regenerate any downstream typed clients once, not four times.
- BE-L2-001 and BE-L2-016 must be co-ordinated: fixing V017's FK action without addressing (or explicitly acknowledging) the destructive `DELETE FROM backtest_runs WHERE user_id IS NULL` risks re-introducing silent data loss during migration replay. Prefer adding a new V018 migration that (a) drops+recreates the FK with `ON DELETE CASCADE` and (b) documents/archives orphan rows before delete.
- FE-L2-003 is the only Important item that *requires* new BE work (WS ticket endpoint). Do not schedule FE-L2-003 alone — pair it with a BE task under Agent D.
- BE-L2-009 (Redis-backed limiter) is the only L-effort BE item. It's a natural pairing with BE-L2-010 (both re-write the limiter dependency); schedule them adjacent.
- FE-L2-005 and FE-L2-006 must be scheduled *after* BE-L2-003 so client regeneration reflects the corrected spec.
- BE-L2-002 fix should live in `backend/api/ws/live.py` and can be trivially unit-tested by injecting a raising fake `get_latest_candles_batch` and asserting the socket stays alive for a second poll — recommend Agent D add a regression test.
