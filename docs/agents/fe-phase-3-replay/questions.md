# Clarifying Questions — FE Phase 3: Replay

Review of [prd.md](./prd.md) + [tech-design.md](./tech-design.md), cross-checked against FE Phase 3 HLD, Phase 4c HLD, and OpenAPI. Questions only — no proposed answers or redesign.

---

## Backend / contract (Agent D confirmation)

### Q1 — Agent D no-op

Tech design §3 / §8 states Agent D is a **no-op** and FE should absorb mixed casing + polish via adapters/timeouts unless a live smoke test proves a hard protocol break.

**Question:** Confirm Agent D ships **zero** backend code changes for this phase (documentation-only acknowledgment), and that Agent E should treat Phase 4c OpenAPI + live WS as the contract source of truth?

### Q2 — REST GET vs WS field casing

OpenAPI `ReplayStateResponse` mixes snake fields (`session_id`, `step_timeframe`, `start`, `latest_available`, `bar_index`) with camel (`queueRemaining`). Phase 4c HLD create examples use camel (`sessionId`, `wsUrl`, `stepTimeframe`), while OpenAPI create response is snake (`session_id`, `ws_url`). Tech design says normalize everything to camel in the FE adapter.

**Question:** For `GET /replay/sessions/{id}` and create `201`, which wire shapes must the normalize layer accept in v1 — snake-only, camel-only, or both — and is OpenAPI or the live FastAPI response the authoritative sample?

### Q3 — Initial cursor vs “paused at anchor”

Phase 4c HLD / buffer docs set fresh-session `cursor_ts` to **one bar before** `start_anchor` (so the clicked bar is not yet revealed). PRD AC-2 / tech-design snapshot example show trail **through** the anchor with `cursor === startAnchor`.

**Question:** After connect + first `snapshot`, should the chart show zero revealed bars (cursor before anchor), the anchor bar already revealed, or something else — and does the first play/step’s first tick introduce the clicked bar?

---

## Frontend — state machine & protocol

### Q4 — Stop vs Replay toggle (mode after teardown)

PRD §4.2 / tech design §4.11 say Stop → `inactive` **or** `pick_anchor` if mode still on. FE HLD teardown text often returns Stop to `inactive`. Toggle-off is separately defined as Stop + `replayMode false`.

**Question:** Does the **Stop** control leave `replayMode` on and return to `pick_anchor`, or turn mode off and go fully `inactive`?

### Q5 — Step while playing / paused (apply path)

Tech design §4.9 says ArrowRight / step should be “protocol-compatible” while playing. Backend `step` emits a `tick_batch` (same channel as play/refill); client clock only drains while `playing`.

**Question:** On step (and ArrowRight), should FE apply the returned tick(s) **immediately** to the trail (even when paused), enqueue them for the interval drain, pause-then-step, or another rule — and must `count: 1` always be sent (backend default count is batch size if omitted)?

### Q6 — Instant seek without snapshot

Backend seek within trail/prefetch moves cursor only and returns `reloaded=false` (WS sends `replay_state`, **no** `snapshot`). Tech design chart path mainly describes seek via `buffer_reset` + snapshot replace.

**Question:** On in-window seek, how should FE rebuild `trailBars` / indicator trail — slice the existing trail to the new cursor locally, request something else, or treat missing snapshot as a bug?

### Q7 — `set_indicators` vs server `playing` state

PRD / tech design: optimistic pause; remain paused until the user presses play. Backend WS handler can set `engine.state = "playing"` again after recompute if it was playing (without necessarily sending a fresh `tick_batch`).

**Question:** After `buffer_reset` + `snapshot` from mid-session indicator change, is client UI phase authoritative (stay paused until Play), or must FE also send `pause` / ignore server `playing` until the user resumes?

### Q8 — `ready` vs `paused`

The phase machine lists both `ready` and `paused`; notes say ready is “equivalent to paused for controls.”

**Question:** Must FE persist distinct `ready` vs `paused` phases in the store/UI, or is a single paused-equivalent phase enough after the first snapshot?

### Q9 — `buffer_loading` timeout vs phase

PRD/tech design: 3s timeout clears the stuck **loading pill**; phase notes say phase “may return to playing/paused.”

**Question:** On timeout with no `buffer_ready`, does client phase leave `buffer_loading` (and to which phase), or only clear the pill while phase stays `buffer_loading` until a later event?

---

## Frontend — chart data path & indicators

### Q10 — Anchor bar click mechanism

PRD requires click-a-bar in `pick_anchor`. Current chart code has crosshair move sync but no click→bar-time path documented in the tech design beyond “subscribe to chart click / crosshair click.”

**Question:** Which interaction is in scope for v1 — lightweight-charts series/chart click with time from the clicked bar, crosshair-position + click, or another gesture — and should clicks be ignored outside `pick_anchor`?

### Q11 — Live chunk manager while connecting / pick_anchor

Tech design: live `useChunkManager` while `inactive` / `pick_anchor` without session; replay trail authoritative when session connected. Connecting spans POST + WS before snapshot.

**Question:** During `connecting` (and after Stop while returning to live), should chunk manager stay paused, keep serving live data under the trail, or hard-switch only after first snapshot / after teardown completes?

### Q12 — Indicator specs on create / `set_indicators`

Create example includes `pane`; Phase 4c HLD create example omits `pane`. OpenAPI `IndicatorSpec.pane` is optional. Indicator store can have duplicate `seriesId`s (e.g. two `EMA_20`) and visibility flags.

**Question:** Exact create/`set_indicators` payload rules for v1: include `pane` or not; send only `visible !== false` specs; and if two actives share a `seriesId`, send both, dedupe, or is that unsupported?

---

## UX / keyboard / chrome

### Q13 — Keyboard focus & Space / ArrowRight

Tech design: Space toggles play/pause when session active; ignore when typing in inputs; ArrowRight steps. SPEC-001 also maps Esc to drawings (not yet in this phase).

**Question:** Should Space / ArrowRight be window-level (with `preventDefault` to avoid page scroll) whenever focus is not in an editable field / `<select>`, including when focus is on bottom-bar buttons — and is Esc in `pick_anchor` allowed to no-op if a future drawing tool is active, or always wins in pick_anchor for v1?

### Q14 — `followReplay` control

PRD/tech design: `followReplay` defaults **on**; no UI control is listed in the bottom bar table.

**Question:** Is follow-cursor v1 always-on with no user toggle, or is a chrome control required?

### Q15 — Connection status “red”

FE HLD mentions connection dot green / amber / **red**. Tech-design `ReplayConnectionStatus` is `idle | connecting | open | amber | closed` (no red).

**Question:** When is connection shown red (if at all) vs amber/`closed` for unrecoverable disconnects and generic errors?

### Q16 — Scrubber when `latestAvailable` is null / equals cursor

Progress formula uses `(cursor − startAnchor) / (latestAvailable − startAnchor)`. OpenAPI allows null `latestAvailable`; completed may have cursor at latest.

**Question:** What should the scrubber render for null or zero denominator (empty, 0%, 100%, disabled), and after `replay_completed` does seeking earlier re-enable Play immediately once phase returns to paused?

---

## Testing

### Q17 — WebSocket test double

Tech design requires mock-WebSocket unit tests for close `4401`/`4404`, relative `ws_url` → absolute URL, and typed dispatch.

**Question:** Is there a required test pattern for this repo (e.g. stub `global.WebSocket`, MSW, or a small fake client injectable into `replayWsClient`), or may Agent E introduce a minimal mock as long as close-code handlers are covered?

### Q18 — App / ChartContainer test mocks after flip

AC-14 flips `App.test` to expect Replay present. ChartContainer tests already mock `useChunkManager`.

**Question:** For App/ChartPage RTL tests in v1, should replay hooks/WS be mocked by default so existing chart tests stay offline, and only dedicated replay tests exercise the real store/WS client with fixtures?

---

## End
