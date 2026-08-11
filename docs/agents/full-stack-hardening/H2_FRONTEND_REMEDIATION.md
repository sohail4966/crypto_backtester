# Agent H2 — Frontend Remediation (pass 2)

**Date:** 2026-08-11  
**Scope:** Frontend-owned findings from `G_CODE_REVIEW.md` (G-002 FE half, G-003, G-010, G-013)  
**Constraint:** `frontend/` only; no commit/push

---

## Summary

All four frontend-owned G findings are addressed. Replay WS close codes now distinguish auth vs superseded; FE-010/011 are wired into `prefetchPriorChunk` with regression tests; dead `/auth/claim` and passwordless `createUser` helpers are removed; minimal backtest markers render on the chart when a run is selected.

**Verification:** `npm test` — 173 passed; `npm run build` — success.

---

## G-002 — Distinct replay WS close codes (Critical, FE half)

**Contract (aligned with BE intent):**
| Code | Meaning | FE behavior |
|------|---------|-------------|
| `4401` | `UNAUTHORIZED` | `notifyAuthFailure` + clear command queue + red connection + toast |
| `4402` | `SUPERSEDED` | Existing “Opened in another tab” amber UX + clear queue |
| `4404` | `NOT_FOUND` | Existing not-found amber UX + clear queue |

**Files:**
- `frontend/src/constants/replay.ts` — `REPLAY_CLOSE_UNAUTHORIZED=4401`, `REPLAY_CLOSE_SUPERSEDED=4402`
- `frontend/src/services/replayWsClient.ts` — `closeKind` maps codes; new `'unauthorized'` reason
- `frontend/src/hooks/useReplayWs.ts` — auth close → queue clear + `notifyAuthFailure('UNAUTHORIZED')`
- `frontend/src/types/replay.ts` — `ReplayConnectionReason` includes `'unauthorized'`
- `frontend/src/services/replayWsClient.test.ts` — updated close-code mapping test

**Note:** At review time `backend/api/ws/replay.py` still closed superseded sockets with `4401`. FE is ready for `4402`; Agent F must update BE superseded close to `4402` so the two paths no longer collide.

---

## G-003 — Wire FE-010 / FE-011 into `useChunkManager` (Important)

**Changes in `prefetchPriorChunk`:**
1. Guard with `hasCoverage(priorStart, priorEnd)` instead of `hasChunk(priorStart)`.
2. Before `addChunk`, if `isRangedFallbackResponse` / empty / no overlap → skip ingest and set `reachedEarliestRef`.
3. Subsequent prefetches no-op once earliest is exhausted; reset on symbol/TF reload.

**Regression tests** (`useChunkManager.test.tsx`):
- FE-010: prefetch path calls `hasCoverage`, never `hasChunk`.
- FE-011: empty/`empty: true` response does not mutate candles; second scroll does not re-fetch.

---

## G-010 — Remove claim / passwordless create helpers (Minor)

**Removed:**
- `createUser` (passwordless `POST /users`)
- `claimUser` (`POST /auth/claim`) and DEV claim fallback in `obtainDevToken`
- `/auth/claim` from `AUTH_EXEMPT_PREFIXES` in `api.ts`
- Claim mock branch in `App.test.tsx`

Dev bootstrap is now register → login only (gated by `allowDevAuth()`).

---

## G-013 — Backtest chart markers (Minor / FE-007)

**Minimal working path (not deferred):**
- `backtestOverlayStore` holds selected runId + signals + trades after a successful run.
- `buildBacktestMarkers` maps signals/trades → lightweight-charts `SeriesMarker`s.
- `BacktestMarkers` applies markers on the candle series when chart symbol/TF matches the run.
- Backtest page sets overlay on success, clears on new submit, links “Open chart”.

**Not in this pass:** re-fetching overlays solely via chart-data `includeSignals`/`includeTrades`/`runId` (run payload is the source for markers). Query flags remain available for a later chart-data-driven path.

---

## Checklist vs G blockers (FE)

| ID | Status |
|----|--------|
| G-002 FE | **Done** (needs BE `4402` for superseded) |
| G-003 | **Done** |
| G-010 | **Done** |
| G-013 | **Done** (minimal markers) |

BE-owned G-001, G-004–G-009, G-011, G-012 remain for Agent F.
