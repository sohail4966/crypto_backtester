# Agent H Report — FE Phase 3: Replay (Final E2E Review)

| Field | Value |
|---|---|
| **Verdict** | **READY_WITH_NITS** |
| **Date** | 2026-08-11 |
| **Inputs** | [prd.md](./prd.md), [tech-design.md](./tech-design.md), [agent-e-report.md](./agent-e-report.md), [agent-f-report.md](./agent-f-report.md), [agent-g-report.md](./agent-g-report.md) |
| **Quality gate** | `frontend/`: `npm test` + `npm run build` — **pass**; `backend/` replay pytest — **pass** (untouched) |

---

## Final verdict

**READY_WITH_NITS** — AC-1..AC-14 are satisfied in code with automated evidence. Agent G critical/important fixes hold; Agent H closed remaining seek/connection edge gaps. Residual risk is **live Phase 4c manual smoke** (create → play → scrub → stop, 4401 second tab, URL resume) and known v1 polish nits (follow-cursor always-on, full `setData` trail path).

---

## AC checklist

| AC | Criterion | Status | Evidence |
|---|---|---|---|
| **AC-1** | Replay toggle beside `+ Add indicator`; pick_anchor banner; no sidebar `/replay` | **PASS** | `ReplayToggle` in `IndicatorsBar`; `ReplayAnchorBanner` on `ChartPage` when `pick_anchor`; `Sidebar` Chart+Backtest only; `App.test` asserts Replay button present + no Replay nav link |
| **AC-2** | Bar click → POST session → WS → snapshot → bottom bar paused at anchor | **PASS** | `useReplayChart` click → `startFromAnchor` → `createReplaySession` + `beginConnect`; empty snapshot accepted; bottom bar via `sessionActivePhase`; `useReplaySession.test` URL write |
| **AC-3** | `/?replaySession=` GET + WS resume, skip pick_anchor | **PASS** | `useReplaySession` resume effect; invalid id toast + clear param (`useReplaySession.test`) |
| **AC-4** | Play / pause / stop / step / speed + Space | **PASS** | `ReplayBottomBar` + `useReplaySession` WS commands; `useReplayKeyboard` Space; `ReplayBottomBar.test`; speed dropdown `0.5–10` |
| **AC-5** | Scrubber progress + D-95 tooltip; seek via protocol | **PASS** | `ReplayScrubber` ratio + tooltip copy; `seek` → `beginSeeking` + WS; in-window slice / oob snapshot replace |
| **AC-6** | Revealed trail only; ticks incremental (no live refetch per bar) | **PASS** | `ChartContainer` uses `trailBars` when `trailAuthoritative`; store drain/append; live chunk render gated |
| **AC-7** | Buffer pill + 3s timeout; completed disables play | **PASS** | `useReplayWs` buffer timer; `ReplayStatusPill`; `pendingCompleted` deferral (Agent G); play disabled when `completed` |
| **AC-8** | `SEEK_OUT_OF_RANGE` toast + snap to last cursor | **PASS** | Toast + `cancelSeek()` clears seek/oob flags without moving cursor; store tests |
| **AC-9** | WS 4401 / 4404 amber + messaging | **PASS** | `replayWsClient` close kinds; toasts; 4401 pause; 4404 → pick_anchor + amber restored after teardown |
| **AC-10** | Mid-session indicator change → pause + `set_indicators` + snapshot path | **PASS** | `useReplayIndicatorSync` + `sendSetIndicators` + `forcePausedUntilPlay` + WS `pause` |
| **AC-11** | Symbol/TF change → teardown → pick_anchor if mode on | **PASS** | `useReplaySession` symbol/TF effect |
| **AC-12** | Esc in pick_anchor → inactive + toggle off | **PASS** | `useReplayKeyboard` Escape handler |
| **AC-13** | Stop / toggle off → DELETE + close WS + live chart | **PASS** | `stopToPickAnchor` / `teardownFully`; `trailAuthoritative` cleared on reset → live path |
| **AC-14** | `npm test` + `npm run build`; App expects Replay present | **PASS** | 22 files / **82** tests; build OK; `App.test` Replay present |

**Gaps:** None blocking. Several ACs rely on unit/RTL + contract wiring rather than live browser E2E (called out under residual risks).

---

## Bugs fixed in this stage (Agent H)

| Severity | Fix | Files |
|---|---|---|
| Important | OOB seek: stay in `seeking` and keep last valid cursor while `awaitingSnapshotReplace` (avoid premature pause / cursor jump before snapshot) | `stores/replayStore.ts` |
| Important | `SEEK_OUT_OF_RANGE` → `cancelSeek()` clears awaiting/expect flags and snaps UI without moving cursor | `stores/replayStore.ts`, `hooks/useReplayWs.ts` |
| Important | WS close clears `expectImmediateTicks` (avoids sticky immediate-apply after aborted step) | `hooks/useReplayWs.ts` |
| Important | 4404: after re-pick teardown, restore amber connection + clearer toast | `components/Replay/ReplayRoot.tsx`, `hooks/useReplayWs.ts` |
| Nit | Remove unused `teardownFully` keyboard option | `hooks/useReplayKeyboard.ts`, `ReplayRoot.tsx` |
| Test | AC-1 no Replay nav link; oob seek + cancelSeek store coverage | `App.test.tsx`, `replayStore.test.ts` |

Agent G critical fixes (client-revealed cursor, deferred `completed`, D-95 tooltip, buffer_ready fresh meta, expectImmediateTicks clears on transport) re-verified — no regressions.

---

## Test results

### Frontend

```
npm test   → 22 files, 82 tests passed
npm run build → tsc -b && vite build succeeded
```

### Backend (optional spot-check; code untouched)

```
backend/.venv/bin/python -m pytest tests/api/ -k replay -q
→ 22 passed, 28 deselected
```

---

## Docs status updates

| Doc | Change |
|---|---|
| `frontend/docs/ROADMAP.md` | Phase 3 **Not started — current focus** → **Complete (v1) — live Phase 4c smoke still recommended**; diagram tag updated |
| `frontend/docs/FE_PHASE_3_HLD.md` | Already **Implemented (v1)** — left consistent |

---

## Residual risks / manual smoke still needed

1. **Live Phase 4c smoke** against running API: create → play → pause → scrub (in-window + oob) → stop; URL paste resume; second-tab **4401**; deleted session **4404**.
2. Follow-cursor always-on may feel jumpy if user pans mid-play (accepted v1 / Q14).
3. Candlestick trail uses full `setData` (visual OK; not per-tick `series.update`).
4. `useChunkManager` still runs under the hood during trail-authoritative replay (render gated).
5. SUPERSEDED / buffer mid-batch edge cases depend on backend polish; FE timeouts/amber cover UX.

---

## Pipeline summary

| Agent | Role | Outcome |
|---|---|---|
| D | Backend | No-op (Phase 4c ready) |
| F | Backend review | Approve — no changes |
| E | Frontend implement | Complete E1–E14 |
| G | Review + fixes | approve-with-nits (critical cursor/complete fixed) |
| **H** | Final gate | **READY_WITH_NITS** |

---

## Artifacts

| Item | Path |
|---|---|
| This report | `docs/agents/fe-phase-3-replay/agent-h-report.md` |
| Working tree | Uncommitted (pipeline convention) |
