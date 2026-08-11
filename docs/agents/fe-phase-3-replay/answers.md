# Answers — FE Phase 3: Replay (Agent B)

Decisive answers for [questions.md](./questions.md). Incorporated into [tech-design.md](./tech-design.md).

---

### Q1 → Answer

**Yes — Agent D ships zero backend code changes** for this phase (documentation-only acknowledgment). Agent E treats **live Phase 4c FastAPI REST + WS code** as the primary contract source of truth, with OpenAPI as a secondary map that can lag on casing. FE absorbs mixed casing and polish via adapters/timeouts. Agent D stays a no-op unless a live smoke test proves a hard protocol break.

### Q2 → Answer

Normalize layer must accept **both** snake and camel for GET and create responses (and WS `replay_state`).

- **Create `201`:** wire is snake-only today (`session_id`, `ws_url`) — still normalize defensively.
- **GET / WS state:** live WS dumps `by_alias=True` → aliased camel (`startAnchor`, `latestAvailable`, `barIndex`, `queueRemaining`) mixed with unaliased snake (`session_id`, `step_timeframe`, `cursor`, `state`, `speed`). REST GET may emit the same alias set via FastAPI defaults; OpenAPI property names are inconsistent — **do not trust OpenAPI alone for casing**.
- **Authoritative sample:** live FastAPI handlers + `ReplayStateResponse` / WS `model_dump(by_alias=True)` in code; OpenAPI for shape/types only.

### Q3 → Answer

After connect + first `snapshot`, the chart shows **zero revealed bars** (empty `bars` / empty indicator trail). Backend sets fresh `cursor_ts` to **one bar before** `start_anchor`; `snapshot_bars()` returns `[]` while `cursor_idx < window_start_idx`. Phase is paused/ready at that cursor. **The first play/step tick introduces the clicked anchor bar.** PRD “paused at the anchor” means UX-ready to reveal from the clicked bar, not “anchor already drawn.”

### Q4 → Answer

**Stop** tears down the session and returns to **`pick_anchor` with `replayMode` still on**. Only the **Replay toggle off** (or Esc in pick_anchor) turns mode off and goes fully `inactive`. Stop ≠ toggle-off.

### Q5 → Answer

On step / ArrowRight: **apply returned `tick_batch` ticks immediately** to the trail (and update cursor/meta), whether paused or playing — do not wait for the interval drain. Do **not** also leave those step ticks in the drain queue (avoid double-apply). Always send **`count: 1`** (backend defaults to full batch size if omitted). While playing, keep the clock running unless the UI explicitly pauses.

### Q6 → Answer

On in-window seek (`reloaded=false`, `replay_state` only): **slice the existing `trailBars` / indicator trail locally** to the new cursor (bars with `time <= cursor`). Not a bug. Only `buffer_reset` + `snapshot` replaces the full trail.

### Q7 → Answer

**Client UI phase is authoritative:** stay paused until the user presses Play. After `buffer_reset` + `snapshot` from mid-session indicator change, force local phase `paused`, stop the clock, and **send `{ action: "pause" }`** to resync the server (backend may set `engine.state = "playing"` again without a fresh batch). Ignore server `playing` until the user resumes.

### Q8 → Answer

A **single paused-equivalent phase is enough** after the first snapshot. Keep `ready` in the type union for HLD alignment if desired, but on first snapshot set store phase to **`paused`** (or immediately alias ready→paused). Do not maintain separate ready vs paused UI chrome.

### Q9 → Answer

On 3s timeout with no `buffer_ready`: **clear the loading pill and leave `buffer_loading`**, restoring phase to the prior transport phase (`playing` or `paused`). Do not remain stuck in `buffer_loading` until a later event.

### Q10 → Answer

v1 interaction: **lightweight-charts `subscribeClick`** (chart/series click) → resolve clicked bar unix `time` → create session. Prefer the bar under the click; if only crosshair time is available, use that as fallback. **Ignore clicks outside `pick_anchor`.**

### Q11 → Answer

During `connecting` (POST + WS before first snapshot): **keep live `useChunkManager` serving** under the UI (no blank chart). **Hard-switch to replay trail only after the first snapshot.** After Stop / teardown completes, resume live chunk path. Do not leave chunk manager paused across the whole connecting window.

### Q12 → Answer

Create / `set_indicators` payload rules for v1:

- **Include `pane`** (`overlay` | `subchart`) — matches `ChartContainer` / `IndicatorSpec`.
- Send **only `visible !== false`** actives.
- **Dedupe** by `key + params + pane` (same as chart-data specs today). Duplicate identical specs → one entry. Distinct params/panes → send all. Unsupported to rely on duplicate identical `seriesId`s server-side.

### Q13 → Answer

Space / ArrowRight are **window-level** (with `preventDefault` to avoid page scroll) whenever focus is **not** in an editable field (`input`, `textarea`, `contenteditable`) or `<select>` — including when focus is on bottom-bar buttons. In `pick_anchor`, **Esc always wins for v1** (dismiss → inactive + toggle off). Drawing-tool Esc ownership is out of scope until drawings ship; do not no-op Esc in pick_anchor.

### Q14 → Answer

`followReplay` is **always-on in v1** (default `true`, no chrome toggle). No bottom-bar control required.

### Q15 → Answer

Connection dot mapping:

- **Green** — `open` / healthy.
- **Amber** — recoverable protocol closes **4401** / **4404** (and transient reconnect ambiguity).
- **Red** — unrecoverable disconnect / generic hard errors / `error` phase.
- **`closed` / idle** — clean teardown or no session (no alarm chrome).

Extend `ReplayConnectionStatus` to include **`red`**.

### Q16 → Answer

Scrubber: if `latestAvailable` is **null** or denominator is **≤ 0**, render **disabled / empty track at 0%** (do not NaN). When `cursor === latestAvailable` (completed), show **100%**. After `replay_completed`, seeking earlier → phase **`paused`** and **Play re-enables immediately**.

### Q17 → Answer

No MSW requirement. Agent E may introduce a **minimal mock** — prefer an injectable WS transport / stub `global.WebSocket` with Vitest `vi.fn` (repo pattern). Must cover close `4401`/`4404`, relative `ws_url` → absolute URL, and typed dispatch.

### Q18 → Answer

**Yes:** App / ChartContainer RTL tests mock replay hooks/WS by default so existing chart tests stay offline. Only dedicated replay unit/hook tests exercise the real store + WS client with fixtures.

---

## Design deltas applied

Updates made in [tech-design.md](./tech-design.md):

1. **§3 Agent D / SoT** — Explicit no-op; live FastAPI+WS primary, OpenAPI secondary; normalize both casings.
2. **§3 / §6 contract** — Fresh-session cursor = one bar before anchor; empty initial snapshot; first tick reveals anchor. Fixed examples.
3. **§4.8–4.11** — Stop → `pick_anchor` + mode on; step immediate apply + `count:1`; in-window seek local slice; `set_indicators` + client pause + WS `pause`; chunk manager during connecting; anchor `subscribeClick`; indicator payload rules (`pane`, visible-only, dedupe).
4. **§4.2 / §5** — `ready` collapses to `paused`; `buffer_loading` timeout restores prior phase; connection status adds `red`; `followReplay` always-on.
5. **§4.7 / §4.9** — Scrubber null/zero-denom + completed seek→play; keyboard window-level + Esc wins in pick_anchor.
6. **§7 Testing** — Injectable/minimal WS mock; App/Chart mock replay by default.
7. **§8 Agent D** — Remains no-op; no Agent D code work discovered.
