# FE Phase 3 High Level Design — Replay

**Status:** Implemented (v1)  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md), [FE Phase 2](FE_PHASE_2_HLD.md)  
**Backend:** ✅ [Phase 4c](../../backend/docs/PHASE_4C_HLD.md) complete — **8.9/10**  
**Spec:** [SPEC-001 §4.5, §5.3–5.4](SPEC-001.md)  
**Decisions:** D-88–D-95 (WS replay, client clock, accelerated speed, clamp pan, progress UI)  
**Roadmap:** [ROADMAP.md — Phase 3](ROADMAP.md#phase-3--replay)

---

## Phase 3 Goal

Replay is a **mode on the live chart page** (`/`), not a separate route. User toggles
replay from the topbar (beside indicator controls), picks a start anchor on the chart,
and progressively reveals bars via WebSocket tick batches and a client-side playback clock.
A bottom control bar appears while a session is active.

---

## Entry Flow

```
Topbar "Replay" toggle (beside + Add indicator)
  → chartStore.replayMode = true; replay phase = pick_anchor
  → banner: "Click a bar to start replay"
  → user clicks a bar
  → POST /api/v1/replay/sessions { symbol, timeframe, start: bar.time, indicators, speed }
  → response { sessionId, wsUrl }
  → open WS, receive replay_state + snapshot
  → bottom bar mounts; phase = ready (paused at anchor)

URL resume: /?replaySession={sessionId}
  → GET /api/v1/replay/sessions/{id}
  → open WS, hydrate store from REST + snapshot
  → bottom bar mounts; skip pick_anchor if session valid
```

**Session create payload:** `symbol.ticker`, `timeframe`, `start` (clicked bar unix sec),
`indicators` from `indicatorStore` (visible specs only), `speed` default `1.0`.

**Teardown (Stop button or toggle replay off):** `DELETE /sessions/{id}`, close WS,
reset `replayStore`, return to `inactive`. Symbol/timeframe change mid-session does the same
then re-enters `pick_anchor` if replay mode is still on.

**Esc in pick_anchor:** dismiss banner, phase → `inactive` (stay on `/`, replay toggle can
stay on or off — default: toggle off).

---

## Navigation Changes

| Before | After |
|---|---|
| Sidebar nav link `/replay` | **Removed** |
| `ReplayPage.tsx` route | **Removed** (or thin redirect to `/`) |
| Topbar `Indicators` label + `+ Add indicator` | **`+ Add indicator` only** + **Replay toggle** beside it |
| Topbar only on `/` | Unchanged — replay mode lives on chart route |

---

## What Gets Built

| Area | Files |
|---|---|
| Types | `types/replay.ts` — WS event unions, `ReplayTick`, session config |
| API | `services/replayApi.ts` — create/get/delete session, `buildWsUrl` |
| WS client | `services/replayWsClient.ts` — connect, send, typed event dispatch |
| Store | `stores/replayStore.ts` — phase machine, tick queue, cursor, buffer flags |
| Store | `chartStore` — add `replayMode: boolean` toggle |
| Hooks | `hooks/useReplaySession.ts` — lifecycle: create / reconnect / teardown |
| Hooks | `hooks/useReplayWs.ts` — wire WS events → store |
| Hooks | `hooks/useReplayTick.ts` — `setInterval` drain + refill threshold |
| Hooks | `hooks/useReplayChart.ts` — chart data path for replay mode |
| UI | `components/Replay/ReplayBottomBar.tsx` — play/pause/**stop**, speed, scrubber |
| UI | `components/Replay/ReplayAnchorBanner.tsx` — pick-anchor prompt |
| UI | `components/Replay/ReplayStatusPill.tsx` — buffer loading, completed, connection |
| UI | `components/ui/Toast.tsx` — minimal inline toasts (no dependency) |
| Topbar | `IndicatorsBar.tsx` — remove label; add Replay toggle |
| Chart | `ChartContainer` `mode` prop — live vs replay data paths |
| Chart | `ReplayCandlestickSeries.tsx` — revealed trail only (v1); `update` per tick |
| Chart | replay indicator series — append points per tick |
| Page | `ChartPage.tsx` — bottom bar + banner when replay active |

**Deferred v1:** `EquityCurve.tsx` (see below). Ghost/dim bars (option C).

**Backend endpoints:**

```
POST   /api/v1/replay/sessions          → { sessionId, wsUrl }
GET    /api/v1/replay/sessions/{id}     → state snapshot (reconnect)
DELETE /api/v1/replay/sessions/{id}     → teardown
WS     /ws/replay/{sessionId}           → snapshot, tick_batch, replay_state, …
```

---

## Replay Phase Machine (client)

```
inactive        — replayMode off, or mode on but idle
pick_anchor     — replayMode on, waiting for bar click
connecting      — POST + WS handshake
ready           — snapshot received, paused at anchor
playing         — client clock draining tick queue
paused          — clock stopped
seeking         — scrubber drag outside trail/prefetch; awaiting buffer_reset + snapshot
buffer_loading  — forward extend in flight (+ 3s timeout fallback)
completed       — replay_completed received; play disabled
error           — unrecoverable; toast + return to pick_anchor or inactive
```

---

## Chart Visual States (v1 — option C)

**No ghost bars.** Only the revealed trail is rendered:

- Initial `snapshot` → `setData` with bars through `cursor`
- Each tick → `series.update(bar)` + indicator point append (O(1))
- Seek / `buffer_reset` + `snapshot` → full `setData` replace

Warmup context and dimmed future bars are **deferred** until backend snapshot includes
full frame or a merged chart-data path is added.

---

## Bottom Bar → Protocol Mapping

| Control | WS / behavior |
|---|---|
| Play | `{ action: "play", speed }` — starts client `setInterval` |
| Pause | `{ action: "pause" }` — stops interval |
| **Stop** | pause + `DELETE` session + close WS → `inactive` (or `pick_anchor` if mode still on) |
| Step → | `{ action: "step", count: 1 }` |
| Speed dropdown | `{ action: "set_speed", speed }` |
| Scrubber | `{ action: "seek", to: unix }` |
| (hidden) Refill | `{ action: "refill" }` when `tickQueue.length < 20` |

**Scrubber:** `(cursor − startAnchor) / (latestAvailable − startAnchor)` with tooltip
explaining moving denominator (**D-95**).

**Buffer pill:** `buffer_loading` → `buffer_ready` + **3s timeout** fallback.

**Completed:** `replay_completed` → badge, play disabled.

**Connection dot:** green / amber (4401 SUPERSEDED, 4404) / red.

---

## Edge Cases

| Scenario | FE behavior |
|---|---|
| `SEEK_OUT_OF_RANGE` | Toast; snap scrubber to last valid `cursor` |
| WS `4404` | Toast + amber dot; offer re-pick anchor |
| WS `4401` SUPERSEDED | Amber dot + "Opened in another tab"; pause clock |
| Indicator toggle mid-play | Optimistic pause → `set_indicators` → `buffer_reset` + `snapshot` |
| Symbol/timeframe change | Teardown session → `pick_anchor` if replayMode on |
| Pan left | Clamp at oldest revealed bar (D-90) |
| `followReplay` default on | Scroll viewport to cursor on tick |

---

## Equity Curve (deferred v1)

SPEC-001 shows an optional **equity curve sub-pane** under the chart during replay — a line
chart of portfolio value over time as bars replay. That data comes from **backtest trades**
(Phase 4d), which the replay WS does not stream today.

**v1:** omit `EquityCurve.tsx` entirely. Bottom bar + candle/indicator replay only.
Revisit when backtest API exposes per-session equity series.

---

## Resolved Decisions

| Question | Decision |
|---|---|
| Ghost bars | **C** — revealed trail only, no dimmed warmup/future |
| Topbar controls | **Yes** — symbol/timeframe/indicators always on `/` |
| Symbol change mid-session | Teardown → `pick_anchor` |
| Esc in pick_anchor | Stay on `/`, phase → `inactive` |
| Toast | Minimal inline component |
| Session resume | `/?replaySession={id}` → GET session + WS reconnect |
| Route vs mode | **Mode on `/`**; remove sidebar Replay link |
| Stop button | **Yes** — explicit teardown |
| Equity curve | **Defer** — no stub in v1 |

---

## Done Criteria

- [ ] Replay toggle in topbar (no sidebar link); `+ Add indicator` without "Indicators" label
- [ ] Pick anchor → session + WS; bottom bar mounts
- [ ] `/?replaySession=` reconnects via GET + WS
- [ ] Play/pause/stop/step/speed/scrubber wired to WS protocol
- [ ] Revealed trail only; O(1) tick via `series.update`
- [ ] D-95 progress scrubber + tooltip
- [ ] Buffer pill + timeout; `replay_completed` state
- [ ] SEEK_OUT_OF_RANGE toast + scrubber snapback
- [ ] 4401/4404 amber connection state
- [ ] Indicator change optimistically pauses
- [ ] `npm run build` + `npm test` pass

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4C_HLD.md](../../backend/docs/PHASE_4C_HLD.md)
- [2026-06-28-replay-v2-design.md](../../docs/superpowers/specs/2026-06-28-replay-v2-design.md)
