# Agent C — Severity & Dependency Rating

**Sources:** `A_BACKEND_ISSUES.md` (BE-001..BE-024), `B_FRONTEND_ISSUES.md` (FE-001..FE-018)  
**Consumers:** Agent F (backend), Agent H (frontend)  
**Scope:** Rating + remediation order only — no fixes in this artifact.

---

## Severity key

| Level | Meaning |
|---|---|
| **Critical** | Auth bypass / forgeable identity, or account takeover in realistic deploy |
| **High** | Data loss with false success, wrong trading results, DoS/cost abuse, or broken core UX (auth session / replay) |
| **Medium** | Integrity gaps, reliability under load, or incorrect secondary UX that does not forge identity |
| **Low** | Incomplete feature surface, polish, or constraints that prevent future bugs but are not actively failing |

Ranks below are a **global** suggested order (`1` = first). Agents F and H should still parallelize within a wave where `Dependency` allows.

---

## Backend issues (BE-001..BE-024)

### BE-001 — Scan persist never commits (API path)
- **Severity:** High
- **Dependency:** none
- **Blocks:** BE-023, FE-006
- **Rationale:** HTTP scan reports success/`persisted=True` while the transaction rolls back, so audit trail and any future retrieve path are lies.
- **Suggested fix order rank:** 5

### BE-002 — Account takeover via `/auth/claim` + passwordless `POST /users`
- **Severity:** Critical
- **Dependency:** none (coordinate message/shape with BE-024; do not delay the claim fix for enumeration polish)
- **Blocks:** BE-024, FE-004
- **Rationale:** Unproven email + passwordless create enables full account takeover and JWT issuance.
- **Suggested fix order rank:** 2

### BE-003 — Hardcoded default JWT secret
- **Severity:** Critical
- **Dependency:** none
- **Blocks:** BE-005, BE-006, FE-002, FE-003, FE-004
- **Rationale:** A public default secret lets anyone mint JWTs for arbitrary `user_id` and pass ownership checks.
- **Suggested fix order rank:** 1

### BE-004 — Unauthenticated expensive compute (DoS / cost)
- **Severity:** High
- **Dependency:** BE-003 (auth gate needs a trustworthy secret/config story)
- **Blocks:** FE-006
- **Rationale:** Public backtest/scan/replay/live/AI with no caps invites CPU/DB exhaustion and LLM bill abuse.
- **Suggested fix order rank:** 6

### BE-005 — Spoofable `user_id` on backtest runs
- **Severity:** High
- **Dependency:** BE-003
- **Blocks:** FE-007 (if FE starts trusting per-user run history)
- **Rationale:** Client-supplied `user_id` forges attribution once JWT auth is meaningful.
- **Suggested fix order rank:** 10

### BE-006 — Replay sessions have no owner; UUID is capability URL
- **Severity:** High
- **Dependency:** BE-003
- **Blocks:** FE-008, FE-009 (auth headers / ownership errors on replay)
- **Rationale:** Unauthenticated create/get/delete/WS lets anyone with a session id hijack or destroy replays.
- **Suggested fix order rank:** 11

### BE-007 — Backtest/scan unix windows truncated to calendar dates
- **Severity:** High
- **Dependency:** none
- **Blocks:** FE-007
- **Rationale:** Inclusive unix windows become midnight-truncated dates, so metrics/signals are systematically wrong vs candle/chart paths.
- **Suggested fix order rank:** 8

### BE-008 — Candle/chart `limit` applied after full-range load
- **Severity:** High
- **Dependency:** none (pairs with BE-004 for abuse surface)
- **Blocks:** FE-010, FE-011 (correct pagination/`next_from` under real SQL limits)
- **Rationale:** Wide ranges still load fully into memory before truncate, enabling OOM/stalls despite a small client `limit`.
- **Suggested fix order rank:** 7

### BE-009 — Derived TF includes incomplete in-progress buckets
- **Severity:** High
- **Dependency:** none
- **Blocks:** FE-005 (live higher-TF bars), FE-007 (near-now overlays)
- **Rationale:** Forming higher-TF aggregates are treated as closed candles in live/backtest/scan paths.
- **Suggested fix order rank:** 13

### BE-010 — `1M` semantics inconsistent (calendar month vs 30 days)
- **Severity:** Medium
- **Dependency:** none
- **Blocks:** FE-016
- **Rationale:** SQL month buckets disagree with API/fetcher 30-day math, breaking warmup/seek/pagination for monthly charts.
- **Suggested fix order rank:** 22

### BE-011 — Migrations race under concurrent startup
- **Severity:** High
- **Dependency:** none
- **Blocks:** BE-014, BE-021, BE-022 (safe concurrent apply of later schema fixes)
- **Rationale:** Multi-instance startup can double-apply migrations and leave half-applied schema.
- **Suggested fix order rank:** 12

### BE-012 — Register/create user not transactional with default watchlist
- **Severity:** Medium
- **Dependency:** none
- **Blocks:** FE-004 (onboarding assumes Default watchlist)
- **Rationale:** Mid-provision failure leaves users without the default watchlist clients expect.
- **Suggested fix order rank:** 14

### BE-013 — Setting `is_default` can clear all defaults if update misses
- **Severity:** Medium
- **Dependency:** BE-014 (unique default constraint reduces blast radius; fix clear-then-miss ordering either way)
- **Blocks:** FE-017
- **Rationale:** Clear-defaults-then-failed-update can leave a user with zero defaults after commit.
- **Suggested fix order rank:** 16

### BE-014 — No uniqueness for “one default watchlist per user”
- **Severity:** Medium
- **Dependency:** BE-011 (migration safety before new constraint)
- **Blocks:** BE-013, FE-017
- **Rationale:** Without a partial unique index, concurrent updates can create multiple defaults and ambiguous client behavior.
- **Suggested fix order rank:** 15

### BE-015 — Email uniqueness is case-sensitive; no format validation
- **Severity:** Medium
- **Dependency:** BE-002 (normalize/validate as part of identity hardening after claim redesign)
- **Blocks:** FE-004
- **Rationale:** Case-variant emails create duplicate logical accounts and login friction; weak format checks hurt identity hygiene.
- **Suggested fix order rank:** 17

### BE-016 — `GET /users` enumerates all users; `GET /users/{id}` public
- **Severity:** High
- **Dependency:** BE-003; coordinate with FE-002 (bootstrap must stop treating public GET as JWT proof)
- **Blocks:** FE-002, FE-003
- **Rationale:** Listing emails/names and public single-user GET leak identity and aid claim targeting (BE-002).
- **Suggested fix order rank:** 4

### BE-017 — CORS localhost regex enabled by default
- **Severity:** High
- **Dependency:** none
- **Blocks:** none
- **Rationale:** Prod-reachable API with default localhost CORS + credentials enables malicious local pages to call authenticated APIs.
- **Suggested fix order rank:** 9

### BE-018 — Replay WS: uncaught bad JSON; long-held DB connection
- **Severity:** Medium
- **Dependency:** BE-006 (ownership/auth changes touch the same handler)
- **Blocks:** FE-008, FE-009
- **Rationale:** Bad frames crash the handler and one held DB connection per socket starves HTTP under fan-out.
- **Suggested fix order rank:** 18

### BE-019 — Live WS opens a new DB connection per symbol per poll
- **Severity:** Medium
- **Dependency:** none
- **Blocks:** FE-005
- **Rationale:** Per-symbol per-poll connect/close churn will not survive FE live adoption.
- **Suggested fix order rank:** 19

### BE-020 — In-memory AI clarify sessions + multi-worker loss
- **Severity:** Medium
- **Dependency:** BE-004 (bind sessions after AI is authenticated/rate-limited)
- **Blocks:** FE-006
- **Rationale:** Process-local unscoped sessions break under multi-worker and allow session continuation by id guess.
- **Suggested fix order rank:** 20

### BE-021 — `data_gaps` weak constraints / duplicate opens
- **Severity:** Low
- **Dependency:** BE-011
- **Blocks:** none
- **Rationale:** Missing FK/CHECK/unique-open constraints allow duplicate overlapping gaps and noisy retries, not immediate user-facing failure.
- **Suggested fix order rank:** 23

### BE-022 — Status / state columns lack CHECK constraints
- **Severity:** Low
- **Dependency:** BE-011
- **Blocks:** none
- **Rationale:** Free-form status TEXT can store invalid literals; defense-in-depth after app paths are correct.
- **Suggested fix order rank:** 24

### BE-023 — Scan repository `get()` unused; no HTTP retrieve
- **Severity:** Medium
- **Dependency:** BE-001
- **Blocks:** FE-006
- **Rationale:** Even after persist works, scans remain unreachable without a retrieve API.
- **Suggested fix order rank:** 21

### BE-024 — Auth claim / login reveal account state (enumeration)
- **Severity:** Medium
- **Dependency:** BE-002
- **Blocks:** none
- **Rationale:** Distinct claim/register errors enable email enumeration and targeting of passwordless accounts.
- **Suggested fix order rank:** 3

---

## Frontend issues (FE-001..FE-018)

### FE-001 — API client drops backend error messages
- **Severity:** High
- **Dependency:** none
- **Blocks:** FE-002, FE-003, FE-004, FE-017
- **Rationale:** Ignoring `{ error: { code, message } }` makes auth/watchlist failures opaque and blocks correct 401 recovery branching.
- **Suggested fix order rank:** 25

### FE-002 — Bootstrap treats public `GET /users/{id}` as proof of valid JWT
- **Severity:** High
- **Dependency:** FE-001; BE-016 (lock down or change contract together)
- **Blocks:** FE-003, FE-004
- **Rationale:** Expired tokens still “bootstrap” because public GET succeeds, then watchlists fail with stale UI state.
- **Suggested fix order rank:** 26

### FE-003 — No 401/403 handling or token refresh anywhere
- **Severity:** High
- **Dependency:** FE-001, FE-002
- **Blocks:** FE-004
- **Rationale:** After JWT expiry, mutations break with no clear/re-auth path until manual storage wipe.
- **Suggested fix order rank:** 27

### FE-004 — Hardcoded silent register/login as the only auth UX
- **Severity:** High
- **Dependency:** FE-001, FE-002, FE-003, BE-002, BE-003, BE-012, BE-015
- **Blocks:** none (enables safe shared-API use of watchlists)
- **Rationale:** Shipping `dev@local` credentials as the only auth path is production-risk and blocks real multi-user use.
- **Suggested fix order rank:** 28

### FE-005 — Live candle WS exists on BE but FE never connects
- **Severity:** Medium
- **Dependency:** BE-009, BE-019
- **Blocks:** none
- **Rationale:** Charts stay frozen on last REST fetch; wire live only after incomplete-bucket and connection-pool issues are fixed.
- **Suggested fix order rank:** 37

### FE-006 — Screener/AI HTTP APIs unused by FE
- **Severity:** Low
- **Dependency:** BE-001, BE-004, BE-020, BE-023, FE-001
- **Blocks:** none
- **Rationale:** Feature gap, not a correctness bug; defer until scan persist/retrieve and AI session/auth hardening land.
- **Suggested fix order rank:** 42

### FE-007 — Backtest response equity/overlays ignored; chart overlays never wired
- **Severity:** Medium
- **Dependency:** BE-007, BE-005, BE-009
- **Blocks:** none
- **Rationale:** BE already returns equity/signals/trades and chart-data overlay flags; FE drops them so analysis UI stays incomplete.
- **Suggested fix order rank:** 36

### FE-008 — Leaving chart route kills replay WS without reconnect
- **Severity:** High
- **Dependency:** FE-009; BE-006, BE-018 (server auth/reliability while reconnecting)
- **Blocks:** none
- **Rationale:** Route change closes WS and resume short-circuits, so replay looks active but Play/Step/Seek no-op.
- **Suggested fix order rank:** 30

### FE-009 — Replay commands silently dropped when socket not open
- **Severity:** High
- **Dependency:** none (helps FE-008; align with BE-018)
- **Blocks:** FE-008
- **Rationale:** Optimistic `playing` without queue/retry desyncs client phase from server advancement.
- **Suggested fix order rank:** 29

### FE-010 — Chunk prefetch key mismatch (`priorStart` vs `data.start`)
- **Severity:** Medium
- **Dependency:** BE-008 (stable `start`/`next_from` under SQL limit)
- **Blocks:** none
- **Rationale:** Prefetch guard key ≠ stored chunk key causes repeated historical refetches and thrash.
- **Suggested fix order rank:** 32

### FE-011 — Empty chart-data windows fall back to latest bars (FE assumes empty/historical)
- **Severity:** High
- **Dependency:** Coordinate with BE chart_data empty-window contract (related to BE-008 pagination semantics)
- **Blocks:** FE-010
- **Rationale:** Gap scroll-back can ingest “latest” bars as a prior chunk, corrupting anchors near holes.
- **Suggested fix order rank:** 31

### FE-012 — Chart legend always shows active-pane symbol/timeframe
- **Severity:** Low
- **Dependency:** none
- **Blocks:** none
- **Rationale:** Multi-chart inactive panes show wrong labels over correct series — confusing but not data-corrupting.
- **Suggested fix order rank:** 35

### FE-013 — Default sync couples visible ranges across unsynced symbols
- **Severity:** Medium
- **Dependency:** none
- **Blocks:** none
- **Rationale:** Default `visibleRange: true` with `symbol: false` jumps/clips multi-symbol viewports incorrectly out of the box.
- **Suggested fix order rank:** 34

### FE-014 — Indicators are global, not per pane
- **Severity:** Low
- **Dependency:** FE-018 (persistence model should match pane scope if both are done)
- **Blocks:** none
- **Rationale:** UX limitation — every pane shares one indicator set; not a security or data-loss bug.
- **Suggested fix order rank:** 41

### FE-015 — Drawing create/hit-test keyed off chartStore, not pane props
- **Severity:** Medium
- **Dependency:** none
- **Blocks:** none
- **Rationale:** Fast pane switches can save/hit-test drawings under the wrong symbol/TF.
- **Suggested fix order rank:** 33

### FE-016 — FE timeframe catalog incomplete vs BE
- **Severity:** Low
- **Dependency:** BE-010 (especially before exposing `1M`)
- **Blocks:** none
- **Rationale:** Valid BE timeframes unreachable from UI; incomplete catalog, not a runtime failure on current defaults.
- **Suggested fix order rank:** 38

### FE-017 — Watchlist FE never uses rename/delete/get-one endpoints
- **Severity:** Low
- **Dependency:** FE-001, BE-013, BE-014
- **Blocks:** none
- **Rationale:** Incomplete CRUD vs BE; orphan lists accumulate but core list/create path works.
- **Suggested fix order rank:** 39

### FE-018 — Active indicators not persisted across reload
- **Severity:** Low
- **Dependency:** none (prefer before FE-014 if both scheduled)
- **Blocks:** FE-014
- **Rationale:** Reload wipes indicator overlays; persistence polish after correctness issues.
- **Suggested fix order rank:** 40

---

## Suggested global fix order (compact)

| Rank | ID | Severity | Owner |
|---:|---|---|---|
| 1 | BE-003 | Critical | F |
| 2 | BE-002 | Critical | F |
| 3 | BE-024 | Medium | F |
| 4 | BE-016 | High | F (+ H for FE-002) |
| 5 | BE-001 | High | F |
| 6 | BE-004 | High | F |
| 7 | BE-008 | High | F |
| 8 | BE-007 | High | F |
| 9 | BE-017 | High | F |
| 10 | BE-005 | High | F |
| 11 | BE-006 | High | F |
| 12 | BE-011 | High | F |
| 13 | BE-009 | High | F |
| 14 | BE-012 | Medium | F |
| 15 | BE-014 | Medium | F |
| 16 | BE-013 | Medium | F |
| 17 | BE-015 | Medium | F |
| 18 | BE-018 | Medium | F |
| 19 | BE-019 | Medium | F |
| 20 | BE-020 | Medium | F |
| 21 | BE-023 | Medium | F |
| 22 | BE-010 | Medium | F |
| 23 | BE-021 | Low | F |
| 24 | BE-022 | Low | F |
| 25 | FE-001 | High | H |
| 26 | FE-002 | High | H |
| 27 | FE-003 | High | H |
| 28 | FE-004 | High | H |
| 29 | FE-009 | High | H |
| 30 | FE-008 | High | H |
| 31 | FE-011 | High | H (+ F contract) |
| 32 | FE-010 | Medium | H |
| 33 | FE-015 | Medium | H |
| 34 | FE-013 | Medium | H |
| 35 | FE-012 | Low | H |
| 36 | FE-007 | Medium | H |
| 37 | FE-005 | Medium | H |
| 38 | FE-016 | Low | H |
| 39 | FE-017 | Low | H |
| 40 | FE-018 | Low | H |
| 41 | FE-014 | Low | H |
| 42 | FE-006 | Low | H |

Ranks 1–24 vs 25–42 are sequential in the table for readability; **Wave 1 FE (25–28) should run in parallel with Wave 1 BE** once BE-003/BE-002/BE-016 contracts are agreed.

---

## Remediation waves

### Wave 1 — Must fix first (auth forgeability, takeover, false persist, DoS, wrong engine windows)

**Backend (Agent F)**
1. **BE-003** — Fail closed without `JWT_SECRET` in non-dev; never ship the hardcoded default.
2. **BE-002** — Kill passwordless claim/create takeover (proof-of-email, disable public passwordless create, or equivalent).
3. **BE-024** — Uniform auth errors after claim redesign (no existence oracle).
4. **BE-016** — Stop public user enumeration / unauthenticated `GET /users/{id}` (or replace with “me” endpoint).
5. **BE-001** — Commit scan inserts on the API connection path; align `persisted` with reality.
6. **BE-004** — Auth and/or rate limits + window/symbol caps on backtest/scan/replay/live/AI.
7. **BE-008** — Push `LIMIT`/keyset into SQL for candles/chart-data.
8. **BE-007** — Pass full timestamptz (not date-truncated) for backtest/scan windows.
9. **BE-017** — Default CORS localhost regex off outside local/dev.

**Frontend (Agent H) — parallel once error/auth contracts known**
1. **FE-001** — Parse `{ error: { code, message } }`.
2. **FE-002** — Prove JWT (authenticated `/me` or equivalent), not public `GET /users/{id}`.
3. **FE-003** — Clear token / re-auth on 401/403.
4. **FE-004** — Replace silent `dev@local` auth with real login/register UX (after BE-002/BE-003).

### Wave 2 — High correctness & ownership gaps

**Backend**
- **BE-005** — Bind `backtest_runs.user_id` from JWT only.
- **BE-006** — Add replay ownership + auth on REST/WS.
- **BE-011** — Advisory lock / single-runner migrations.
- **BE-009** — Exclude incomplete derived TF buckets (or mark explicitly).

**Frontend**
- **FE-009** — Queue/retry replay commands until WS OPEN; don’t fake `playing`.
- **FE-008** — Reconnect/resume after route remount (depends on FE-009).
- **FE-011** — Don’t treat latest-fallback as historical prior chunk (pair with BE empty-window contract).
- **FE-010** — Unify prefetch keys with returned `data.start`.

### Wave 3 — Integrity, reliability under load, product wiring

**Backend**
- **BE-012** — Transactional user + default watchlist provision.
- **BE-014** then **BE-013** — Unique default + safe `is_default` update ordering.
- **BE-015** — Normalize/validate emails.
- **BE-018** — Catch bad replay JSON; don’t hold one DB conn for WS lifetime.
- **BE-019** — Pool/reuse live WS DB access before FE live adoption.
- **BE-020** — Durable, user-bound AI clarify sessions.
- **BE-023** — Expose scan retrieve HTTP after BE-001.
- **BE-010** — Align `1M` calendar-month vs 30-day semantics.

**Frontend**
- **FE-015** — Pane-prop-aware drawing create/hit-test.
- **FE-013** — Fix default multi-chart sync coupling.
- **FE-012** — Per-pane legend labels.
- **FE-007** — Wire equity/signals/trades overlays (after BE-007/BE-005/BE-009).
- **FE-005** — Connect `/ws/live` (after BE-019 + BE-009).

### Wave 4 — Nice-to-have / defer if needed

**Backend**
- **BE-021** — Gap table FK/CHECK/unique-open constraints.
- **BE-022** — CHECK constraints on status/state columns.

**Frontend**
- **FE-016** — Load `/meta/timeframes` (after BE-010 for `1M`).
- **FE-017** — Watchlist rename/delete/default UI (after BE-013/BE-014).
- **FE-018** then **FE-014** — Persist indicators; then per-pane indicator state.
- **FE-006** — Screener/AI UI (after BE-001, BE-004, BE-020, BE-023, FE-001).

---

## Cross-cutting notes

### FE depends on BE
| FE issue | Needs BE first / together | Why |
|---|---|---|
| **FE-002, FE-003** | **BE-016**, **BE-003** | Bootstrap/auth recovery must match lockdown of public user GET and real JWT verification. |
| **FE-004** | **BE-002**, **BE-003**, **BE-012**, **BE-015** | Real auth UX is unsafe/broken if claim takeover, default JWT secret, or incomplete onboarding remain. |
| **FE-005** | **BE-019**, **BE-009** | Live client would amplify connection churn and publish incomplete higher-TF bars. |
| **FE-006** | **BE-001**, **BE-004**, **BE-020**, **BE-023** | Scan UI needs durable+retrievable runs; AI UI needs auth/rate limits and durable sessions. |
| **FE-007** | **BE-007**, **BE-005**, **BE-009** | Overlay/equity UI is misleading until windows, attribution, and closed-bar semantics are correct. |
| **FE-008, FE-009** | **BE-006**, **BE-018** | Reconnect/auth errors and stable WS handlers should land with client queue/resume work. |
| **FE-010, FE-011** | **BE-008** (+ chart_data empty-window contract) | FE chunk keys/anchors depend on honest pagination and empty-range behavior. |
| **FE-016** | **BE-010** | Exposing `1M` before month-vs-30d alignment spreads wrong seek/warmup. |
| **FE-017** | **BE-013**, **BE-014** | Default toggle/rename UI should not hit the clear-all-defaults footgun. |

### BE depends on FE (or must ship coordinated)
| BE issue | Needs FE coordination | Why |
|---|---|---|
| **BE-016** | **FE-002** | If `GET /users/{id}` becomes auth-only or removed, bootstrap must switch in the same release. |
| **BE-002 / BE-024** | **FE-004** | Claim/register error shapes and flows change; silent `dev@local` path must not keep using insecure claim. |
| **BE-006** | **FE-008 / FE-009** | Replay REST/WS will start returning 401; client must send Bearer and handle auth failures. |
| **BE-005** | **FE-007** / backtest client | Drop client `user_id`; FE must stop sending spoofable ids. |
| **BE-004** | Any FE calling scan/AI/backtest anonymously | FE will need tokens once endpoints require auth. |
| Chart empty-window (FE-011 driver) | **FE-011** | Prefer BE returning empty + explicit flag over silent latest-fallback; FE must handle the new contract. |

### Parallelization guidance for Agents F & H
- **Start together:** F on Wave 1 BE-003/002/016/001/004/008/007/017; H on FE-001 immediately, then FE-002/003 as soon as BE-016 contract is decided.
- **Do not start FE-005 or FE-006 early** — they amplify unfinished BE reliability/security debt.
- **Replay track:** F BE-006 + BE-018 alongside H FE-009 → FE-008.
- **Chart data track:** F BE-008 (+ empty-window policy) alongside H FE-011 → FE-010.

---

## Counts

| Severity | BE | FE | Total |
|---|---:|---:|---:|
| Critical | 2 | 0 | 2 |
| High | 11 | 7 | 18 |
| Medium | 9 | 5 | 14 |
| Low | 2 | 6 | 8 |
| **Total** | **24** | **18** | **42** |

Wave membership: **W1** = Critical + highest-urgency High (auth/DoS/false persist/wrong windows + FE auth path); **W2** = remaining High ownership/correctness; **W3** = Medium integrity/reliability/wiring; **W4** = Low / deferrable feature surface.
