# PRD — FE Phase 5: Drawings (MVP)

| Field | Value |
|---|---|
| **Status** | Approved (auto — no human in loop; defaults resolved in §9) |
| **Phase** | Frontend Phase 5 |
| **Product intent** | [FE_PHASE_5_HLD.md](../../../frontend/docs/FE_PHASE_5_HLD.md) |
| **Architecture** | [SPEC-001](../../../frontend/docs/SPEC-001.md) §5.5–5.6, §8.3 |
| **Backend** | None required — IndexedDB only (D-85 interim); Phase 4d deferred |
| **Decisions** | D-83 (MVP tool scope), D-84 (Price Range primitive), D-85 (IndexedDB until 4d) |

---

## 1. Problem / Goal

### Problem

Analysts can view candles, indicators, replay, and watchlists, but cannot annotate the chart with trend structure, levels, risk ranges, or notes. Without drawings, chart analysis requires external tools and annotations are lost on reload.

### Goal

Deliver five MVP drawing tools on the main chart so a local analyst can:

1. Select a tool from a toolbar (or keyboard shortcut).
2. Place the drawing with chart clicks.
3. See it rendered with resolved hex colors (no CSS `var()` passed to lw-charts).
4. Select and delete drawings; cancel an in-progress placement with Esc.
5. Reload the app and recover drawings scoped to the same `symbolId` + `timeframe` from IndexedDB.

Success means annotations survive reload without any backend workspace sync.

---

## 2. User Roles

| Role | Need | Identity model |
|---|---|---|
| **Analyst / trader** | Place levels, ranges, and notes while studying a market. | Same browser-local session as Phase 4; no login. |
| **Developer / QA** | Verify tool placement, persistence, shortcuts, and non-regression of replay/watchlist. | Same public API + IndexedDB. |

---

## 3. Scope

### In scope

- Five tools: Trend Line, Horizontal Line, Rectangle, Price Range, Text Note.
- `drawingStore` (Zustand) as interaction + in-memory source of truth for the session.
- IndexedDB persistence of all drawings (hydrate on boot; write on mutation).
- Scope filter: drawings for active `chartStore.symbol.id` + `chartStore.timeframe`.
- `DrawingToolbar` in the chart top chrome (beside indicators / replay).
- `DrawingsLayer` inside `ChartContainer` via `ChartContext`.
- Click-to-place via `chart.subscribeClick()`:
  - Horizontal Line — 1 click (price).
  - Text Note — 1 click (anchor) + text prompt.
  - Trend Line / Rectangle — 2 clicks.
  - Price Range — 3 clicks (entry → target → stop).
- Keyboard: `D` `H` `R` `P` `T`, `Esc`, `Delete` / `Backspace`.
- Colors stored as resolved hex at creation (`resolveChartColor`).
- Selection highlight + Delete removes selected drawing.
- Tests for store, cache, keyboard, and placement/render wiring; `npm test` + `npm run build`.

### Out of scope

- Fibonacci, channels, rays, vertical lines, brushes, pattern tools (SPEC-002).
- Server workspace sync (`GET/POST /workspace`) — Phase 4d.
- Drag-to-edit anchors (optional stretch in HLD; deferred).
- Multi-chart pane drawings (Phase 6).
- Equity curve annotations.
- Backend schema, routes, or migrations.

### Current product baseline

- Chart click subscription exists for replay anchor pick (`useReplayChart`).
- Replay keyboard owns Space / ArrowRight / Esc (pick_anchor only).
- `resolveChartColor` already used across chart series.
- IndexedDB via `idb-keyval` proven in watchlist cache.
- No drawing types, store, or toolbar exist yet.

---

## 4. UX Flows

### 4.1 Place trend line

```text
User presses D (or clicks Trend in toolbar)
  → activeTool = trend_line; cursor affordance
  → first chart click → draft p1 (time, price)
  → second click → addDrawing; clear tool + draft
  → DrawingsLayer renders line series between p1–p2
```

### 4.2 Place horizontal line

One click → `horizontal_line` at price; tool clears.

### 4.3 Place rectangle

Two clicks → `topLeft` / `bottomRight` (normalized so first/second order does not matter); tool clears.

### 4.4 Place price range

Three clicks at prices: entry, target (TP), stop (SL). Renders three levels, shaded risk zone (entry↔stop), and HTML R:R label. Tool clears after third click.

### 4.5 Place text note

One click → `window.prompt` for text → empty cancel aborts without creating; non-empty creates `text_note`.

### 4.6 Select / delete / cancel

- Click near an existing drawing (hit-test) selects it when no tool is active (or after cancel).
- `Delete` / `Backspace` removes selected drawing.
- `Esc`: cancel draft + clear active tool; if no draft/tool, deselect.

### 4.7 Symbol / timeframe switch

Filter redraws for the new key. Drawings for other keys remain in store/IndexedDB.

### 4.8 Reload

App hydrates drawings from IndexedDB before/with chart mount; matching symbol+tf drawings appear.

### 4.9 Coexistence with replay / watchlist

- During `pick_anchor`, drawing click handlers do not consume clicks (replay owns them).
- Drawing shortcuts ignore editable targets (inputs), same as replay.
- Esc: drawing cancel/deselect takes precedence when a drawing tool/draft/selection is active; otherwise replay Esc behavior stands.
- Watchlist and symbol search remain unchanged.

---

## 5. Acceptance Criteria

| ID | Criterion |
|---|---|
| **AC-1** | Toolbar exposes all five tools; active tool is visually indicated. |
| **AC-2** | Shortcuts `D/H/R/P/T` activate tools when focus is not in an editable field. |
| **AC-3** | Trend line: two clicks create a persisted `trend_line` with hex color. |
| **AC-4** | Horizontal line: one click creates `horizontal_line` with hex color. |
| **AC-5** | Rectangle: two clicks create `rectangle` with fill opacity. |
| **AC-6** | Price range: three clicks create `price_range` with entry/target/stop + R:R overlay. |
| **AC-7** | Text note: one click + non-empty prompt creates `text_note`. |
| **AC-8** | Drawings filter by active `symbolId` + `timeframe`. |
| **AC-9** | Mutations persist to IndexedDB; reload restores drawings. |
| **AC-10** | `Esc` cancels draft/tool; second Esc (or Esc with no tool) deselects. |
| **AC-11** | `Delete`/`Backspace` deletes the selected drawing. |
| **AC-12** | No lw-charts color parse errors — colors are hex, never raw `var(--*)`. |
| **AC-13** | Replay pick-anchor and watchlist flows still work (no regressions). |
| **AC-14** | Relevant unit/integration tests; `npm test` and `npm run build` pass. |

---

## 6. Non-goals / Explicit exclusions

- Equity / fib / advanced TA tools.
- Collaborative or multi-device sync.
- Touch-only gesture set (mouse/keyboard MVP is enough).
- Custom color picker UI beyond default theme accent hex.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Click handler conflict with replay | Gate drawing subscribeClick when `phase === 'pick_anchor'`; document Esc precedence. |
| Rectangle/price-range fill fidelity in lw-charts | Use HTML overlay positioned via `timeToCoordinate` / `priceToCoordinate`. |
| Persist race on rapid mutations | Debounced write; always serialize full drawings array. |
| Keyboard clash with typing in search | Reuse `isEditableTarget` guard. |

---

## 8. Success metrics (engineering)

- All AC-1..AC-14 pass with automated evidence where practical.
- `npm test` and `npm run build` green.
- ROADMAP / FE_PHASE_5_HLD marked Complete (v1) after Agent H.

---

## 9. Auto-approved product decisions

1. **Persistence:** IndexedDB is sole source of truth for MVP; no API calls.
2. **Default color:** Resolved accent hex at creation (`var(--color-accent)` → hex for current theme).
3. **Price range click order:** entry → target → stop (three clicks).
4. **Text input:** `window.prompt`; empty/cancel does not create.
5. **Drag-edit:** Deferred; select + delete only.
6. **Toolbar placement:** Chart route topbar / IndicatorsBar cluster.
7. **Rectangle normalization:** Min/max time and price so order of clicks does not matter.
8. **Hit-test selection:** Pixel-threshold near geometry when no active tool / no draft.
9. **Delete keys:** Both `Delete` and `Backspace`.
10. **Cache key:** Single versioned blob `drawings:v1` holding all drawings.
11. **Replay Esc precedence:** Drawing cancel/deselect first when relevant.
12. **No backend work** for Agent D.
