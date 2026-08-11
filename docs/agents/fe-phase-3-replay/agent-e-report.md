# Agent E Report — FE Phase 3: Replay (Frontend)

| Field | Value |
|---|---|
| **Verdict** | **Complete** — E1–E14 implemented |
| **Date** | 2026-08-11 |
| **Inputs** | [tech-design.md](./tech-design.md), [prd.md](./prd.md), [answers.md](./answers.md), [agent-d-report.md](./agent-d-report.md) |
| **Quality gate** | `npm test` + `npm run build` in `frontend/` — **pass** |

---

## Summary

Full frontend Replay mode on `/`: types/normalize, REST + WS clients, Zustand phase machine, session/URL/WS/tick/chart/keyboard hooks, UI chrome (toggle, banner, bottom bar, speed, scrubber, status), chart revealed-trail path, mid-session indicator sync, and tests. Backend left untouched (Agent D no-op).

---

## Files created

### Types / constants / utils
- `frontend/src/types/replay.ts`
- `frontend/src/constants/replay.ts`
- `frontend/src/utils/replayNormalize.ts`
- `frontend/src/utils/replayIndicators.ts`

### Services
- `frontend/src/services/replayApi.ts`
- `frontend/src/services/replayApi.test.ts`
- `frontend/src/services/replayWsClient.ts`
- `frontend/src/services/replayWsClient.test.ts`

### Stores
- `frontend/src/stores/replayStore.ts`
- `frontend/src/stores/replayStore.test.ts`

### Hooks
- `frontend/src/hooks/useReplaySession.ts`
- `frontend/src/hooks/useReplaySession.test.tsx`
- `frontend/src/hooks/useReplayWs.ts`
- `frontend/src/hooks/useReplayTick.ts`
- `frontend/src/hooks/useReplayTick.test.tsx`
- `frontend/src/hooks/useReplayChart.ts`
- `frontend/src/hooks/useReplayKeyboard.ts`
- `frontend/src/hooks/useReplayIndicatorSync.ts`

### UI
- `frontend/src/components/Replay/ReplayToggle.tsx`
- `frontend/src/components/Replay/ReplayAnchorBanner.tsx`
- `frontend/src/components/Replay/ReplayBottomBar.tsx`
- `frontend/src/components/Replay/ReplayBottomBar.test.tsx`
- `frontend/src/components/Replay/ReplayScrubber.tsx`
- `frontend/src/components/Replay/ReplaySpeedSelect.tsx`
- `frontend/src/components/Replay/ReplayStatusPill.tsx`
- `frontend/src/components/Replay/ReplaySessionContext.tsx`
- `frontend/src/components/Replay/ReplayRoot.tsx`

---

## Files changed

- `frontend/src/stores/chartStore.ts` — `replayMode` + `setReplayMode`
- `frontend/src/components/Layout/AppShell.tsx` — wraps chart route with `ReplayRoot`
- `frontend/src/components/Layout/IndicatorsBar.tsx` — mounts `ReplayToggle`
- `frontend/src/pages/ChartPage.tsx` — banner + bottom bar
- `frontend/src/components/Chart/ChartContainer.tsx` — trail vs live data path, pan/follow/anchor click via `useReplayChart`
- `frontend/src/app/App.test.tsx` — expects Replay button present; mocks tick/WS hooks
- `frontend/src/components/Chart/ChartContainer.test.tsx` — click subscribe mocks + replay store reset

---

## E1–E14 checklist

| Task | Status |
|---|---|
| E1 types + constants | Done |
| E2 replayApi + normalize tests | Done |
| E3 replayWsClient + mock WS tests | Done |
| E4 replayStore + phase/queue tests | Done |
| E5 chartStore.replayMode | Done |
| E6 useReplaySession + URL sync | Done |
| E7 useReplayWs → store | Done |
| E8 useReplayTick + refill | Done |
| E9 UI chrome | Done |
| E10 chart trail path / clamp / follow / anchor | Done |
| E11 mid-session indicators + symbol/TF teardown | Done |
| E12 keyboard Space / ArrowRight / Esc | Done |
| E13 toasts (SEEK_OUT_OF_RANGE, 4401, 4404, errors) | Done |
| E14 App.test flip + component/hook tests + build | Done |

---

## Test / build results

```
npm test   → 22 files, 78 tests passed
npm run build → tsc -b && vite build succeeded
```

Notable new coverage:
- Store phase/queue/seek/buffer timeout/reset
- API normalize (snake + camel)
- WS URL resolve, send, close 4401/4404
- `useReplayTick` interval + refill + pause stop
- `useReplaySession` URL write/clear, Stop → pick_anchor, invalid resume
- `ReplayBottomBar` / `ReplayScrubber` / banner
- `App.test` asserts Replay button present

---

## Contract adaptations (from Agent D)

- Normalize mixed snake/camel on REST + WS
- Create response → `{ sessionId, wsUrl }` from `session_id` / `ws_url`
- Step always `{ action: "step", count: 1 }` with immediate trail apply
- Fresh snapshot `bars: []` accepted; first tick reveals anchor
- After `set_indicators`: force local pause + send WS `pause`

---

## Known gaps / concerns

1. **Manual smoke not run** against live Phase 4c (create → play → scrub → stop, second-tab 4401, URL resume). Unit/RTL coverage only.
2. **Follow-cursor** refits visible range on every trail length change — may feel jumpy if user pans mid-play; matches v1 “always on” (Q14).
3. **In-window seek detection** uses `awaitingSnapshotReplace` after `buffer_reset`; if backend ever sends only `replay_state` for an oob seek, trail slice path would activate incorrectly (unlikely per Agent D).
4. **CandlestickSeries** still uses full `setData` on trail updates (not incremental `update` per tick) — correct visually; could optimize later.
5. **ReplayRoot** mounts session hooks only on `/`; toggle lives in topbar via shared provider — backtest route has no replay chrome.
6. **Esc in pick_anchor** clears mode locally; no DELETE needed (no session yet). Drawing-tool Esc ownership deferred per answers.

---

## Artifacts

| Item | Path |
|---|---|
| This report | `docs/agents/fe-phase-3-replay/agent-e-report.md` |
| Working tree | Uncommitted (per instructions) |
