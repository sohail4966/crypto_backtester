# Replay V2 Design — WebSocket Streaming with Precomputed Rolling Buffer

**Status:** Approved (brainstorming 2026-06-28)  
**Backend HLD:** [PHASE_4C_HLD.md](../../../backend/docs/PHASE_4C_HLD.md)  
**Decisions:** D-88 through D-94 in [DECISIONS.md](../../../backend/docs/DECISIONS.md)  
**Supersedes:** D-80 (REST replay chunks for FE), amends D-71, partially supersedes D-78  

---

## Problem

Phase 4b shipped REST replay chunks and a WebSocket step API that **recomputes all indicators
over the full prefix on every tick**. This does not scale, cannot deliver near-zero-lag playback,
and has no extension point for signals or chart patterns.

## Goal

WebSocket-first replay where:

1. Playback feels instant (O(1) per bar after buffer load).
2. Memory stays bounded (rolling 500-bar trail + forward prefetch).
3. Sessions are open-ended from a start anchor until latest candle or user stop.
4. Session metadata persists in Postgres; in-memory holds the hot buffer.
5. `OverlayPipeline` extends to signals/patterns later without changing tick logic.

## Architecture

```
Frontend                         Backend
────────                         ───────
replayStore                      ReplayEngine
  ├─ tick queue (client)           ├─ cursor + state machine
  ├─ revealedBars                  ├─ ReplayBuffer (OHLCV + overlays)
  └─ setInterval (speed clock)     ├─ OverlayPipeline → IndicatorService
       │                           └─ ReplaySessionStore (DB + cache)
       │ WS
       ▼
  play / pause / step / seek / refill
       ◄── snapshot, tick_batch, buffer_reset, replay_state
```

## Buffer model

At cursor position 800:

```
[ warmup (internal) ] [ trail: 301–800 ] [ prefetch: 801–1300+ ]
                              ↑
                         cursor (last revealed bar)
```

| Region | Size (default) | Purpose |
|--------|----------------|---------|
| Warmup | Indicator-dependent | Lookback for overlay compute; not shown |
| Trail | 500 bars | Visible history; older bars dropped |
| Prefetch | 1000 bars | Precomputed forward bars ready to stream |

- **Extend:** When cursor is within 200 bars of prefetch edge, background fetch + compute.
- **Seek back >500:** Reload buffer anchored at seek target.
- **End:** No fixed `end` — stops at latest DB candle → `replay_completed`.

## Playback speed (D-89)

- **Accelerated model:** `1×` = 1 bar per second (timeframe-independent).
- **Client owns the clock:** `intervalMs = max(50, 1000 / speed)`.
- **Server pre-slices tick batches** (100 ticks); client drains queue locally.
- **No server asyncio autoplay loop.**

## Zoom / pan (D-90)

- Zoom and pan are **client-only** viewport operations on revealed data.
- Pan left **clamps** at oldest revealed bar; Jump to server.
- Jump/seek beyond trail triggers server `buffer_reset`.
- `followReplay` toggle (default on) scrolls viewport with cursor.

## Persistence (D-93)

- **DB:** Session metadata + cursor checkpoint (`app.replay_sessions`).
- **Memory:** Hot `ReplayBuffer` only; rebuilt on reconnect from candles.
- **Idle eviction:** Drop memory cache; DB row kept for resume.

## REST removal (D-94)

Remove (or return 410):

- `POST /api/v1/replay/runs`
- `GET /api/v1/replay/{run_id}/chunk`
- `GET /api/v1/replay/{run_id}/trades`

Keep:

- `POST /api/v1/replay/sessions`
- `GET /api/v1/replay/sessions/{id}`
- `DELETE /api/v1/replay/sessions/{id}`
- `WS /ws/replay/{session_id}`

## Scope (v1)

**In:** Candles + indicators over WebSocket, rolling buffer, DB sessions, tick batches.  
**Out:** Signals, chart patterns, trades (Phase 4c backtest / Phase 5 patterns plug into `OverlayPipeline` later).

## References

- [PHASE_4C_HLD.md](../../../backend/docs/PHASE_4C_HLD.md) — implementation plan
- [FE_PHASE_3_HLD.md](../../../frontend/docs/FE_PHASE_3_HLD.md) — frontend replay
- [SPEC-001 §4.5](../../../frontend/docs/SPEC-001.md)
