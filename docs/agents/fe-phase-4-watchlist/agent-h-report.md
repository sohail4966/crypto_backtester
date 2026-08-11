# Agent H Report — FE Phase 4: Watchlist (Final E2E Review)

| Field | Value |
|---|---|
| **Verdict** | **READY_WITH_NITS** |
| **Date** | 2026-08-11 |
| **Inputs** | [prd.md](./prd.md), [tech-design.md](./tech-design.md), [agent-e-report.md](./agent-e-report.md), [agent-f-report.md](./agent-f-report.md), [agent-g-report.md](./agent-g-report.md) |
| **Quality gate** | `frontend/`: `npm test` + `npm run build` — **pass**; backend users/watchlists pytest — **pass** (untouched) |

---

## Final verdict

**READY_WITH_NITS** — AC-1..AC-16 are satisfied in code with automated evidence. Agent G important fixes hold; Agent H added cache-first / empty-Default App coverage and soft-error Retry. Residual risk is **live API smoke** (first-run bootstrap, add from search, reload cache) rather than missing product behavior.

---

## AC checklist

| AC | Criterion | Status | Evidence |
|---|---|---|---|
| **AC-1** | Bootstrap creates Dev User, stores UUID, no duplicate on reload | **PASS** | `userBootstrap.ts` + `userBootstrap.test`; `App.test` first-startup stores `user_id` |
| **AC-2** | EMAIL_EXISTS recovery; stale UUID clear + one retry | **PASS** | `ensureUserId` / `findUserByExactEmail`; WatchlistRoot `USER_NOT_FOUND` one-shot recovery; bootstrap tests |
| **AC-3** | Cache-first paint; successful GET canonical + IndexedDB | **PASS** | `WatchlistRoot` hydrate→refresh→`applyCanonical`→`writeWatchlistCache`; `App.test` deferred GET paints ETH then BTC |
| **AC-4** | Select `is_default`, else lowest `sort_order`, else first | **PASS** | `selectWatchlistId` + normalize/store tests |
| **AC-5** | No lists → create empty **Default** and select | **PASS** | `loadCanonicalWatchlists`; `App.test` asserts POST `{ name: "Default", symbols: [] }` |
| **AC-6** | Sidebar watchlist without removing nav/settings/collapse | **PASS** | `Sidebar` inserts `WatchlistPanel` between nav and settings; `App.test` Watchlist region |
| **AC-7** | Row → complete `Symbol` to `setSymbol`; active semantics | **PASS** | `WatchlistRow` button + `aria-current`; panel/row tests |
| **AC-8** | 250 ms debounce; structured results; loading/empty/error | **PASS** | `SymbolSearch` + tests |
| **AC-9** | Result body switches chart, updates input, closes menu | **PASS** | `SymbolSearch.test` selection case |
| **AC-10** | Add → `PUT …/symbols`, no chart switch, cache after success | **PASS** | `addSymbolToSelected` + search add test; G fix keeps UI after PUT if resolve fails |
| **AC-11** | Duplicate shows **Added**; no request | **PASS** | `hasSymbol` + SymbolSearch Added test |
| **AC-12** | Failed add rolls back + toast; cache untouched | **PASS** | rollback path + toast test; G: rollback only when PUT fails |
| **AC-13** | Create named list, select, add to selected | **PASS** | Panel create + selector; store commit preserves selection |
| **AC-14** | Price column `—`; no live WS/polling | **PASS** | `WatchlistRow` literal `—` |
| **AC-15** | Full `Symbol` entities; IDs from `symbol.id` | **PASS** | Domain types + normalize/API |
| **AC-16** | Relevant tests; `npm test` + `npm run build` | **PASS** | 29 files / **124** tests; build OK |

**Gaps:** None blocking. Live browser smoke against a running API is still recommended.

---

## Bugs fixed in this stage (Agent H)

| Severity | Fix | Files |
|---|---|---|
| Important | Soft refresh failure exposes **Retry** beside inline error (cached rows kept) | `WatchlistPanel.tsx`, panel test |
| Test / AC-3 | App cache-first paint before deferred GET | `App.test.tsx` |
| Test / AC-5 | Empty watchlist list creates Default without redundant GET | `App.test.tsx` |
| Build | Typed mock fetch helper so `tsc -b` accepts App fixtures | `App.test.tsx` |

Agent G important fixes (empty-list resolve short-circuit, no rollback after successful PUT, stale banner gated on refreshing/hydrating) re-verified — no regressions.

---

## Test results

### Frontend

```
npm test   → 29 files, 124 tests passed
npm run build → tsc -b && vite build succeeded
```

### Backend (spot-check; code untouched)

```
PYTHONPATH=backend uv run pytest backend/tests/api/test_users_watchlists.py -q
→ 2 passed
```

---

## Docs status updates

| Doc | Change |
|---|---|
| `frontend/docs/ROADMAP.md` | Phase 4 **Not started** → **Complete (v1) — live API smoke still recommended**; diagram tag updated |
| `frontend/docs/FE_PHASE_4_HLD.md` | **Not started** → **Implemented (v1)**; done criteria checked; endpoints aligned to nested contract |
| `docs/agents/PIPELINE_QUEUE.md` | Phase 4 marked **COMPLETE** / READY_WITH_NITS; next = drawings |

---

## Residual risks / manual smoke still needed

1. **Live API smoke:** cold start → Default list → search Add → reload shows cache then reconcile; create second list; collapse/expand sidebar.
2. Duplicate-email recovery pages `GET /users` (dev-only; no email filter).
3. Concurrent Adds to one list are UI-serialized via pending disable; no dedicated multi-tab conflict handling (out of scope).

---

## Pipeline summary

| Agent | Role | Outcome |
|---|---|---|
| D | Backend | No-op (nested users/watchlists ready) |
| F | Backend review | Approve — no changes |
| E | Frontend implement | Complete |
| G | Review + fixes | approve-with-nits (resolve/PUT/stale banner) |
| **H** | Final gate | **READY_WITH_NITS** |

---

## Artifacts

| Item | Path |
|---|---|
| This report | `docs/agents/fe-phase-4-watchlist/agent-h-report.md` |
| Working tree | Uncommitted (pipeline convention) |
