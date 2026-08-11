# Agent G Report — FE Phase 3: Replay (Review + Fixes)

| Field | Value |
|---|---|
| **Verdict** | **approve-with-nits** |
| **Date** | 2026-08-11 |
| **Reviewed** | Agent E frontend replay implementation vs [tech-design.md](./tech-design.md), [prd.md](./prd.md), [answers.md](./answers.md) |
| **Quality gate** | `npm test` + `npm run build` in `frontend/` — **pass** after fixes |

---

## Findings (severity)

### Critical

1. **Client revealed cursor overwritten by server prefetch tip** — `replayStore.enqueueTicks` adopted `tick_batch.cursor`, and `applyReplayState` always took server `cursor`. After `play`/`refill`, the scrubber jumped to the end of the prefetched batch while the chart only revealed bars as the client clock drained. Spec: browser owns the playback clock; progress UI must track revealed trail (D-95 / client clock).

2. **`replay_completed` stopped the clock before the local queue drained** — `markCompleted` / `serverState === 'completed'` set phase `completed` immediately. The last `tick_batch` often still sits in `tickQueue`; completing early left undrained bars never applied (AC-6 / AC-7).

### Important

3. **Scrubber tooltip missing D-95 moving-denominator copy** — title showed cursor times only; AC-5 requires explaining that progress uses live `latestAvailable` as denominator.

4. **`expectImmediateTicks` could stick after failed/aborted step** — play/pause/seek/error/clearQueue did not clear the flag; a later play batch could apply immediately and skip queue semantics.

5. **`buffer_ready` used stale `store.meta`** — `applyReplayState` spread meta captured at handler entry, risking overwrite of newer cursor/queue fields.

### Nits (not fixed / acceptable)

- Follow-cursor refits on every trail length change (Agent E known; v1 always-on).
- Candlestick path uses full `setData` rather than incremental `series.update` (visual OK).
- `useChunkManager` still runs under the hood during trail-authoritative replay (range updates gated; live candles ignored for render).
- Manual smoke vs live Phase 4c still not run.
- Unused `teardownFully` arg on `useReplayKeyboard` options type.

---

## Fixes applied

| Fix | Files |
|---|---|
| Preserve client-revealed cursor after trail is authoritative (except seek/`sliceTrail` / connecting); `enqueueTicks` updates `queueRemaining` only | `stores/replayStore.ts` |
| `pendingCompleted` flag; defer `completed` until `drainOne` empties queue | `stores/replayStore.ts` |
| Clear `expectImmediateTicks` on play/pause/seek/error/`clearQueue` | `stores/replayStore.ts`, `hooks/useReplaySession.ts` |
| Fresh `getState().meta` on `buffer_ready` | `hooks/useReplayWs.ts` |
| D-95 tooltip text on scrubber | `components/Replay/ReplayScrubber.tsx` |
| Unit tests for cursor preservation, deferred completed, tooltip | `stores/replayStore.test.ts`, `components/Replay/ReplayBottomBar.test.tsx` |

---

## Spec compliance re-check (post-fix)

| Area | Status |
|---|---|
| URL `?replaySession=` write/clear / resume | OK |
| Empty snapshot trail; first tick reveals anchor | OK |
| Stop → `pick_anchor` + mode on; toggle-off → inactive | OK |
| Step `count: 1` + immediate apply | OK |
| `set_indicators` + force pause + WS `pause` | OK |
| Buffer 3s timeout restores prior phase | OK |
| 4401 / 4404 amber + toasts | OK |
| Keyboard Space / ArrowRight / Esc in pick_anchor | OK |
| Revealed trail only; no equity / ghosts | OK |
| Client cursor / deferred completed | **Fixed** |
| D-95 scrubber tooltip | **Fixed** |

---

## Remaining nits

See Findings → Nits above. None block merge for v1.

---

## Test / build results after fixes

```
npm test   → 22 files, 81 tests passed
npm run build → tsc -b && vite build succeeded
```

---

## Final verdict

**approve-with-nits** — Critical/Important correctness gaps fixed; remaining items are polish / manual smoke / known v1 tradeoffs.
