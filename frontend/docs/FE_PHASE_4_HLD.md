# FE Phase 4 High Level Design — Replay

**Status:** Not started  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md), [FE Phase 2](FE_PHASE_2_HLD.md) recommended  
**Backend:** [Phase 4b](../../backend/docs/PHASE_4B_HLD.md) ✅  
**Spec:** [SPEC-001 §4.5, §5.3–5.4](SPEC-001.md)  
**Decisions:** D-80 (REST chunks; no replay WebSocket in FE MVP)  
**Roadmap:** [ROADMAP.md — Phase 4](ROADMAP.md#phase-4--replay)

---

## Phase 4 Goal

`/replay` page progressively reveals bars using a browser-side playback clock. Data arrives
via REST chunks; the frontend owns play/pause/step/speed/jump timing.

---

## What Gets Built

| Area | Files |
|---|---|
| Types | `types/replay.ts` — `ReplayChunk`, replay status union |
| API | `services/replay.ts` — `createReplayRun`, `fetchReplayChunk`, `fetchReplayTrades` |
| Store | `stores/replayStore.ts` — state machine, buffer, `revealedBars` |
| Hooks | `hooks/useReplayTick.ts` — `setInterval`, prefetch threshold |
| UI | `ReplayToolbar.tsx`, `SpeedControl.tsx`, `DateSelector.tsx`, `EquityCurve.tsx` (stub) |
| Chart | `ChartContainer` replay mode — `series.update()` per tick |
| Markers | `TradeMarkers.tsx` — empty until Phase 4c trades |
| Page | `pages/ReplayPage.tsx` |

**Backend endpoints:**

```
POST /api/v1/replay/runs              body: { symbolId, timeframe, start, end, ... }
GET  /api/v1/replay/{runId}/chunk?from=&limit=
GET  /api/v1/replay/{runId}/trades    → [] until Phase 4c
```

---

## Replay State Machine (SPEC-001 §4.5)

```
IDLE → (init) → IDLE
IDLE → (play) → PLAYING
PLAYING → (pause) → PAUSED
PAUSED  → (play)  → PLAYING
PLAYING → (stop)  → STOPPED
PAUSED  → (stop)  → STOPPED
STOPPED → (init)  → IDLE
```

**Prefetch:** When `buffer.length - bufferIndex < REPLAY_PREFETCH_THRESHOLD`, fetch next
chunk in background and `appendChunk`.

---

## Architecture Notes

- **No replay WebSocket** — D-80; do not wire `/ws/replay`.
- **Chunk shape:** Each chunk is a `ChartDataResponse` window (candles + indicators + signals).
- **Jump-to-date:** Stop loop, clear buffer, fetch chunk anchored at target `from`, resume.
- **Speed:** `intervalMs = baseInterval / speed` (1× = one bar per candle period).
- **Keyboard:** `Space` play/pause, `→` step forward (wire in Phase 6 or here).

---

## Done Criteria

Phase 4 is **complete** when:

- [ ] `POST /replay/runs` creates session; first chunk loads on init
- [ ] Play reveals bars one-by-one via `series.update()`
- [ ] Pause / stop / step-forward work correctly
- [ ] Speed control changes tick rate (e.g. 1×, 5×, 10×)
- [ ] Buffer prefetches next chunk before underrun
- [ ] Jump-to-date re-anchors without crash
- [ ] Indicators in replay chunks stay aligned with revealed bars

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4B_HLD.md](../../backend/docs/PHASE_4B_HLD.md)
