# FE Phase 3 High Level Design — Replay

**Status:** Not started  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md), [FE Phase 2](FE_PHASE_2_HLD.md) recommended  
**Backend:** [Phase 4c](../../backend/docs/PHASE_4C_HLD.md) (Replay V2 WebSocket)  
**Spec:** [SPEC-001 §4.5, §5.3–5.4](SPEC-001.md)  
**Decisions:** D-88–D-95 (WS replay, client clock, accelerated speed, clamp pan, progress UI)  
**Roadmap:** [ROADMAP.md — Phase 3](ROADMAP.md#phase-3--replay)

---

## Phase 3 Goal

`/replay` page progressively reveals bars using a **browser-side playback clock** and a
**WebSocket tick queue**. The backend precomputes indicators in a rolling buffer and
streams `tick_batch` messages; the frontend drains them at the selected speed.

---

## What Gets Built

| Area | Files |
|---|---|
| Types | `types/replay.ts` — `ReplayTick`, WS event unions, session types |
| API | `services/replay.ts` — `createReplaySession`, WebSocket client |
| Store | `stores/replayStore.ts` — state machine, tick queue, `revealedBars` |
| Hooks | `hooks/useReplayTick.ts` — `setInterval`, refill threshold |
| Hooks | `hooks/useReplayWs.ts` — connect, dispatch WS events |
| UI | `ReplayToolbar.tsx`, `SpeedControl.tsx`, `DateSelector.tsx`, `EquityCurve.tsx` (stub) |
| Chart | `ChartContainer` replay mode — `series.update()` per tick |
| Markers | `TradeMarkers.tsx` — empty until backtest trades API |
| Page | `pages/ReplayPage.tsx` |

**Backend endpoints:**

```
POST   /api/v1/replay/sessions          → { sessionId, wsUrl }
GET    /api/v1/replay/sessions/{id}     → state snapshot
DELETE /api/v1/replay/sessions/{id}     → teardown
WS     /ws/replay/{sessionId}           → snapshot, tick_batch, replay_state, …
```

**Not used:** `POST /replay/runs`, `GET /replay/{id}/chunk` (removed in Phase 4c).

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

**Refill:** When `tickQueue.length < REPLAY_TICK_REFILL_THRESHOLD`, send WS `{ action: "refill" }`.

**Important:** WS `play` sends **one** `tick_batch` only — there is no server autoplay loop (D-88).
Continuous playback requires the client `setInterval` loop to drain the queue and call `refill`
when low. Calling `play` once without a client tick loop stops after the first batch (~100 bars).

---

## Architecture Notes

- **WebSocket replay** — D-91; wire `/ws/replay/{sessionId}` (supersedes D-80 REST chunks).
- **Client owns clock** — D-88; `intervalMs = max(50, 1000 / speed)`.
- **Speed** — D-89; 1× = one bar per second (accelerated, not candle-period real-time).
- **Initial load:** WS `snapshot` on connect (trail bars + indicators to cursor).
- **Jump-to-date:** WS `{ action: "seek", to }` → expect `buffer_reset` + `snapshot`.
- **Zoom/pan** — D-90; client-only on revealed bars; pan clamps; no WS on zoom.
- **followReplay:** Default on — viewport tracks cursor; user can disable to inspect history.
- **Progress bar (D-95):** `(cursor - startAnchor) / (latestAvailable - startAnchor)`;
  `latestAvailable` updates live when new candles land in DB.
- **Do not use `queueRemaining` for user-facing progress** — prefetch depth only.
- **Keyboard:** `Space` play/pause, `→` step forward (wire in Phase 6 or here).

---

## Done Criteria

Phase 3 is **complete** when:

- [ ] `POST /replay/sessions` creates session; WS connects and receives `snapshot`
- [ ] Play drains `tick_batch` queue; bars reveal via `series.update()`
- [ ] Pause / stop / step-forward work correctly
- [ ] Speed control changes tick rate (1×, 5×, 10× bars/sec)
- [ ] Refill requests next batch before queue underrun
- [ ] Jump-to-date sends seek; chart resets from `buffer_reset` / `snapshot`
- [ ] Indicators update per tick (delta points from batch)
- [ ] Pan/zoom work without WS; pan clamps at oldest revealed bar
- [ ] `replay_completed` handled when backend reaches latest candle

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4C_HLD.md](../../backend/docs/PHASE_4C_HLD.md)
- [2026-06-28-replay-v2-design.md](../../docs/superpowers/specs/2026-06-28-replay-v2-design.md)
