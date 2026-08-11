# PRD — FE Phase 3: Replay

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human-in-loop; product defaults below) |
| **Phase** | Frontend Phase 3 (current focus) |
| **Product intent** | [FE_PHASE_3_HLD.md](../../../frontend/docs/FE_PHASE_3_HLD.md) |
| **Architecture** | [SPEC-001 §4.5](../../../frontend/docs/SPEC-001.md) |
| **Backend** | ✅ [Phase 4c Replay V2](../../../backend/docs/PHASE_4C_HLD.md) (complete, 8.9/10) |
| **Decisions** | D-88–D-95 (client clock, WS tick batches, progress UI); D-69 (no auth) |

---

## 1. Problem / Goal

### Problem

Analysts studying historical price action today can only view a static live chart window. There is no way to step through bars over time, re-experience how indicators unfolded, or scrub to a past moment while keeping backend-computed overlays aligned. Older SPEC/roadmap text implied a separate `/replay` page; that splits context from the chart the user already configured (symbol, timeframe, indicators).

### Goal

Ship **replay as a mode on the live chart page (`/`)** so a user can:

1. Toggle replay from the topbar.
2. Click a bar as the start anchor.
3. Progressively reveal candles and indicators via WebSocket tick batches.
4. Control playback with play / pause / stop / step / speed / scrub — with the **browser owning the playback clock** and the **backend owning cursor + precomputed overlays**.

Success looks like: one uninterrupted chart workspace where “live view” and “historical playback” share the same symbol, timeframe, and indicator setup, without leaving `/`.

---

## 2. User Roles

| Role | Description | Auth |
|---|---|---|
| **Analyst / trader (local chart client)** | Primary user. Runs the Vite app against a local or shared API, studies charts, adds indicators, then replays from a chosen bar. | None — all API routes public per **D-69**. No login, JWT, or user-scoped replay sessions in this phase. |
| **Developer / QA** | Verifies WS reconnect, error codes (4401/4404), and scrubber edge cases. | Same — no auth. |

Multi-user identity, session ownership, and “my replays” are out of scope until Phase 11 auth.

---

## 3. Scope

### In scope (v1)

- Replay **mode** on `/` (not a dedicated product route).
- Topbar **Replay** toggle beside `+ Add indicator`.
- **Pick-anchor** flow: banner prompt → click bar → create session.
- Session lifecycle against Phase 4c:
  - `POST /api/v1/replay/sessions`
  - `GET /api/v1/replay/sessions/{id}` (URL resume)
  - `DELETE /api/v1/replay/sessions/{id}` (teardown)
  - `WS /ws/replay/{sessionId}` (snapshot, tick_batch, state, buffer, completed, errors)
- Bottom control bar: play, pause, **stop**, step-forward, speed, scrubber.
- Client-side playback clock draining a local tick queue; refill when queue is low.
- Chart shows **revealed trail only** (no dimmed future / warmup ghost bars).
- Indicator series appended per tick from WS payloads (visible indicators from session create / `set_indicators`).
- Status surfaces: buffer loading pill (+ timeout fallback), completed badge, connection status, toasts for recoverable errors.
- Mid-session: indicator change (optimistic pause + recompute), symbol/timeframe change (teardown → pick-anchor if mode still on).
- Pan clamp at oldest revealed bar; optional follow-cursor viewport.
- Navigation cleanup: no sidebar `/replay` link; no product dependency on `ReplayPage` (redirect-only if anything remains).
- Update tests that currently assert the Replay button is **absent**.

### Out of scope / deferred

| Item | Reason |
|---|---|
| Equity curve sub-pane | Needs backtest equity series (Phase 4d); omit entirely in v1 — no stub. |
| Ghost / dim bars (warmup or future) | Deferred until snapshot/frame merge supports it (HLD option C). |
| Signals, trades, patterns in replay | Backend OverlayPipeline v1 = indicators only. |
| Separate `/replay` product page | Superseded by mode-on-`/`. |
| JWT / auth / user-owned sessions | D-69 / Phase 11. |
| Changing step timeframe mid-session | Backend: set at create only. |
| Multi-chart replay | Phase 6 layouts; v1 is single chart on `/`. |
| Backend work | Phase 4c already shipped — FE consumes existing contract. |

### Current codebase baseline (as of PRD)

- Chart + indicators (Phases 1–2) exist; `ToastProvider` already wired.
- **No** `replayStore`, **no** `components/Replay/*`, **no** replay WS client.
- Sidebar already has Chart + Backtest only (no Replay nav).
- `App.test` asserts Replay button is **not** present — must flip when feature ships.
- HLD status may say “Implemented”; **treat as not started** until code exists (roadmap: Not started / current focus).

---

## 4. UX Flows

### 4.1 Enter replay (happy path)

```
User on / (live chart with symbol, TF, indicators)
  → clicks Topbar "Replay" toggle
  → replayMode on; phase = pick_anchor
  → banner: "Click a bar to start replay"
  → user clicks a candle
  → POST /replay/sessions { symbol ticker, timeframe, start: bar.time, visible indicators, speed: 1.0 }
  → open WS; receive replay_state + snapshot
  → bottom bar mounts; phase = ready (paused at anchor)
  → chart setData(revealed trail through cursor)
```

### 4.2 Playback controls

| Control | User expectation |
|---|---|
| **Play** | Bars (and indicators) advance at selected speed; Space toggles play/pause when session active. |
| **Pause** | Clock stops; trail stays; can resume or scrub. |
| **Stop** | Explicit teardown: pause + DELETE session + close WS → inactive (or pick_anchor if toggle still on). Chart returns to live data path. |
| **Step →** | Advance exactly one bar (paused or playing per protocol). |
| **Speed** | Accelerated model: 1× = 1 bar/sec; higher = more bars/sec (cap per backend min interval). |
| **Scrubber** | Seek to time along `(cursor − startAnchor) / (latestAvailable − startAnchor)`; tooltip explains moving denominator (D-95). |

Hidden: client requests **refill** when tick queue depth is low — not a user-facing control.

### 4.3 Seek / scrub

- Drag/release scrubber → `seek` to unix time.
- In-window seeks feel instant; out-of-prefetch seeks show buffer/reset then new snapshot.
- `SEEK_OUT_OF_RANGE` → toast; scrubber snaps to last valid cursor.

### 4.4 Stop / teardown

Triggered by **Stop**, turning **Replay toggle off**, or leaving session intentionally:

1. DELETE session (best-effort).
2. Close WebSocket.
3. Reset replay store; `replayMode` off if toggle drove teardown.
4. Chart switches back to live `chart-data` / chunk path.

### 4.5 URL resume

- Landing on `/?replaySession={sessionId}`:
  - GET session → open WS → hydrate from REST + snapshot.
  - Skip pick_anchor if session valid; mount bottom bar at ready/paused (or completed if already done).
- Invalid / missing session → toast; clear query param; remain on live chart (inactive).

### 4.6 Esc (pick_anchor only)

- Esc dismisses banner; phase → **inactive**; **Replay toggle off** (HLD default).
- User stays on `/`.

### 4.7 Symbol or timeframe change mid-session

1. Teardown active session (DELETE + close WS).
2. If `replayMode` still on → return to **pick_anchor** (new banner for new context).
3. If mode off → inactive live chart for the new symbol/TF.

### 4.8 Indicator change mid-play

1. Optimistic pause.
2. Send `set_indicators` with visible specs.
3. Expect `buffer_reset` + `snapshot`; resume only when user presses play (or auto-ready paused).

### 4.9 Error / connection states

| Condition | UX |
|---|---|
| Buffer extending | Status pill “loading”; **3s timeout** fallback to clear stuck loading UI. |
| `replay_completed` | Completed badge; play disabled; user may scrub back / stop. |
| WS close **4404** (not found) | Toast + amber connection; offer re-pick anchor. |
| WS close **4401** SUPERSEDED | Amber + copy that session opened in another tab; pause local clock. |
| Unrecoverable error | Toast; return to pick_anchor or inactive. |
| Connection healthy | Green status dot. |

### 4.10 Chart interaction while replaying

- Only revealed bars are drawn (v1 — no ghosts).
- Pan left clamps at oldest revealed bar (D-90).
- `followReplay` default **on**: viewport tracks cursor on tick.

---

## 5. UI Surfaces

| Surface | Behavior |
|---|---|
| **Topbar Replay toggle** | Beside `+ Add indicator` in indicators bar. On = enter/exit mode. Label: “Replay”. |
| **`+ Add indicator`** | Remains; no separate “Indicators” label required (HLD). |
| **Anchor banner** | Shown in `pick_anchor`; dismissible via Esc or toggle off. |
| **Bottom bar** | Mounted when session is connecting/ready/playing/paused/seeking/buffer_loading/completed. Contains transport controls + scrubber + status pill / connection dot. |
| **Status / toasts** | Buffer, completed, connection, SEEK_OUT_OF_RANGE, 4401/4404, generic errors. Prefer existing toast infrastructure. |
| **Sidebar** | Chart + Backtest only — **no Replay nav link**. |
| **Routes** | Product UX lives on `/`. Do not revive `/replay` as a destination; unknown paths already redirect to `/`. |

---

## 6. Acceptance Criteria

Testable done-when (maps to roadmap + HLD):

1. **AC-1 — Mode entry:** Topbar shows a Replay toggle next to `+ Add indicator`; clicking it enters `pick_anchor` and shows the anchor banner. No sidebar link to `/replay`.
2. **AC-2 — Session start:** Clicking a bar creates a session via `POST /replay/sessions`, opens WS, applies snapshot, mounts the bottom bar, and leaves the chart paused at the anchor.
3. **AC-3 — URL resume:** Visiting `/?replaySession={validId}` reconnects via GET + WS, skips pick_anchor, and restores bottom bar + trail without requiring a new bar click.
4. **AC-4 — Transport:** Play, pause, stop, step-forward, and speed change are available and drive the Phase 4c WS protocol; Space toggles play/pause while a session is active.
5. **AC-5 — Scrubber:** Progress scrubber reflects `(cursor − startAnchor) / (latestAvailable − startAnchor)` with a tooltip explaining the moving denominator (D-95); seek updates the trail via protocol (instant or snapshot replace).
6. **AC-6 — Revealed trail:** Chart renders only revealed bars/indicators; each forward tick uses incremental update (not full live chart-data refetch per bar).
7. **AC-7 — Buffer & complete:** Buffer-loading pill appears on forward extend and clears on ready or after ~3s timeout; `replay_completed` shows completed state and disables play.
8. **AC-8 — Seek errors:** `SEEK_OUT_OF_RANGE` shows a toast and snaps the scrubber to the last valid cursor.
9. **AC-9 — Connection codes:** WS 4401 and 4404 produce amber connection state and user-visible messaging (superseded / re-pick).
10. **AC-10 — Indicators mid-session:** Changing visible indicators while in session pauses optimistically and refreshes from `buffer_reset` + `snapshot`.
11. **AC-11 — Symbol/TF mid-session:** Changing symbol or timeframe tears down the session; if Replay mode remains on, UI returns to pick_anchor.
12. **AC-12 — Esc:** In pick_anchor, Esc dismisses the banner, turns Replay off, and leaves the user on `/` with the live chart.
13. **AC-13 — Stop:** Stop (or toggle off with active session) deletes the session, closes WS, and restores live chart behavior.
14. **AC-14 — Quality gate:** `npm run build` and `npm test` pass; App-level tests expect the Replay control to exist (replacing the current “absent” assertion).

---

## 7. Non-Goals / Deferred

- Equity curve during replay (Phase 4d backtest data).
- Ghost / dimmed warmup or future bars.
- Trade markers / signals driven by replay ticks.
- Auth, multi-device session ownership, or sharing UI beyond raw `replaySession` URL.
- Dedicated Replay page or marketing route.
- Multi-pane / multi-chart replay sync.
- Backend protocol changes (consume Phase 4c as-is).

---

## 8. Dependencies

| Dependency | Status | Notes |
|---|---|---|
| FE Phase 1 — Core chart | ✅ Complete | Candles, windowing, symbol/TF on `/` |
| FE Phase 2 — Indicators | ✅ Complete | Catalog + overlay/sub-pane; visible specs feed session create |
| Backend Phase 4c — Replay V2 | ✅ Complete | REST sessions + WS v2; D-88–D-95 |
| OpenAPI / WS contract | ✅ Available | `POST/GET/DELETE /replay/sessions`, `WS /ws/replay/{id}` |
| Toast UI | ✅ Present | Reuse; extend messages as needed |
| Auth (Phase 11) | ❌ Not required | D-69 public API |

**Assumption:** Local/dev API implements Phase 4c; FE does not ship alternate REST chunk replay (removed in 4c).

---

## 9. Product Decisions (auto-resolved)

| # | Question | Decision |
|---|---|---|
| 1 | URL write-back on create | **Yes** — on successful session create, replace/push `?replaySession={id}` so refresh/share works. Clear the param on teardown. |
| 2 | Speed control shape | **Discrete dropdown** — `0.5 / 1 / 2 / 5 / 10` (HLD). No continuous slider in v1. |
| 3 | Arrow-Right step | **In v1** — Arrow-Right steps one bar when a session is active (SPEC §8.3). |
| 4 | Post-completed affordance | **No dedicated “Replay from anchor” button** — Stop to exit; scrubber may seek earlier; play stays disabled at completed until user seeks/stops. |

Resolved earlier (do not re-open without new evidence): mode-on-`/` (not route); no ghost bars; no equity curve stub; Esc turns toggle off; Stop is required; symbol/TF change → teardown → pick_anchor.

---

## 10. References

- [frontend/docs/FE_PHASE_3_HLD.md](../../../frontend/docs/FE_PHASE_3_HLD.md) — primary UX/design intent
- [frontend/docs/ROADMAP.md](../../../frontend/docs/ROADMAP.md) — Phase 3 status & done-when
- [frontend/docs/SPEC-001.md](../../../frontend/docs/SPEC-001.md) — §4.5 replay architecture, §8.3 shortcuts
- [backend/docs/PHASE_4C_HLD.md](../../../backend/docs/PHASE_4C_HLD.md) — Replay V2 backend (available)
- [backend/docs/DECISIONS.md](../../../backend/docs/DECISIONS.md) — D-69, D-88–D-95
