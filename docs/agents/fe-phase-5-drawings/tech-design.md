# Technical Design — FE Phase 5: Drawings (MVP)

| Field | Value |
|---|---|
| Status | Ready for implementation (post B2 answers) |
| Product requirements | `docs/agents/fe-phase-5-drawings/prd.md` |
| Frontend intent | `frontend/docs/FE_PHASE_5_HLD.md` |
| Backend dependency | None |
| Backend work (Agent D) | **No-op** — verify no workspace drawing API is required |
| Implementation order | Agent D verification → Agent E frontend |

## 1. Summary

Phase 5 adds a frontend-only drawings domain. Users activate one of five tools, place geometry with chart clicks, and see results rendered through lw-charts primitives plus HTML overlays. Zustand `drawingStore` owns session state; IndexedDB holds a versioned blob of all drawings. No backend routes, schemas, or sync.

## 2. Architecture

### 2.1 Component and data flow

```text
AppShell
  └─ DrawingsRoot (hydrate IndexedDB → drawingStore; persist on change)
       └─ (existing WatchlistRoot / ReplayRoot)

Topbar / IndicatorsBar
  └─ DrawingToolbar ── setActiveTool / clearTool

ChartContainer
  ├─ useDrawingInteraction (subscribeClick when tool active; hit-test select)
  ├─ useDrawingKeyboard (D/H/R/P/T, Esc, Delete)
  └─ DrawingsLayer (filter by symbolId+timeframe)
       ├─ lw-charts: createPriceLine / addLineSeries
       └─ HTML overlay: rectangle fills, price-range zones, text, R:R label
```

### 2.2 Ownership boundaries

| Owner | Responsibility |
|---|---|
| `drawingStore` | `drawings[]`, `activeTool`, `selectedId`, `draft` anchors, CRUD |
| IndexedDB (`drawingCache`) | Persist full validated `drawings:v1` blob |
| `DrawingsRoot` | Hydrate once on mount; subscribe and debounce-persist |
| `useDrawingInteraction` | Click placement + hit-test selection; draft local to store |
| `DrawingsLayer` | Pure render from filtered drawings + chart APIs |
| `chartStore` | Symbol/timeframe only — drawings never mutate chart domain |
| Replay | Owns pick_anchor clicks; drawings gated off during that phase |

### 2.3 Domain model

Match SPEC-001 §5.5:

```ts
type DrawingType =
  | 'trend_line'
  | 'horizontal_line'
  | 'rectangle'
  | 'price_range'
  | 'text_note'

interface BaseDrawing {
  id: string
  type: DrawingType
  symbolId: string
  timeframe: string
  color: string // resolved hex
  visible: boolean
  createdAt: number
}

// Discriminated union — see types/drawing.ts
```

Draft state (not persisted):

```ts
type DrawingDraft =
  | { type: 'trend_line' | 'rectangle'; p1: Point }
  | { type: 'price_range'; entryPrice: number; targetPrice?: number }
  | null
```

### 2.4 Click placement rules

| Tool | Clicks | Commit fields |
|---|---|---|
| `horizontal_line` | 1 | `price`, `lineWidth: 1`, `style: 'solid'` |
| `text_note` | 1 + prompt | `anchorTime`, `anchorPrice`, `text` |
| `trend_line` | 2 | `p1`, `p2`, `lineWidth: 2` |
| `rectangle` | 2 | normalized `topLeft` / `bottomRight`, `fillOpacity: 0.15` |
| `price_range` | 3 | `entryPrice`, `targetPrice`, `stopPrice` |

Price/time from `MouseEventParams`: prefer `param.time` + `candleSeries.coordinateToPrice(param.point.y)`. If time missing (off bars), ignore click.

### 2.5 Rendering strategy

| Type | Render |
|---|---|
| `horizontal_line` | `candleSeries.createPriceLine({ price, color, lineWidth, lineStyle })` |
| `trend_line` | `chart.addLineSeries` with two UTC points |
| `rectangle` | HTML absolute div using time/price → pixel; border + fill |
| `price_range` | Three price lines (entry accent, target bull-tint, stop bear-tint derived from stored color) + HTML risk fill + R:R label |
| `text_note` | HTML label at coordinate |

On chart pan/zoom, overlays re-measure via `subscribeVisibleLogicalRangeChange` / `subscribeCrosshairMove` or requestAnimationFrame sync when visible range changes. Prefer: recompute positions in an effect that depends on drawings + a `viewportEpoch` bumped on visible-range change.

Cleanup: remove series/price lines on unmount or drawing removal.

### 2.6 Selection / delete

When `activeTool == null` and `draft == null`, click runs hit-test:

- Horizontal / price-range levels: `|y - priceToCoordinate(price)| < 6`
- Trend: distance to segment < 6 px
- Rectangle / text: bounding box contains point

Selected drawing gets thicker stroke / outline. `Delete`/`Backspace` → `removeDrawing(selectedId)`.

### 2.7 Keyboard

`useDrawingKeyboard` on `window`:

- Skip when `isEditableTarget`
- `d/h/r/p/t` (case-insensitive, no modifiers) → `setActiveTool`
- `Escape` → clear draft + tool; else clear selection (return early so replay Esc still works when nothing drawing-related)
- `Delete`/`Backspace` → delete selected

Replay Space/ArrowRight unchanged. During `pick_anchor`, drawing tool activation is allowed but clicks are ignored until phase exits (toolbar may show tool; user Esc clears).

### 2.8 Colors

On create:

```ts
const color = resolveChartColor('var(--color-accent)', theme)
```

Never pass `var(--*)` into lw-charts options. Theme toggle does not rewrite existing drawing colors in MVP (stored hex remains).

### 2.9 Persistence

```ts
// constants/drawings.ts
DRAWINGS_CACHE_VERSION = 1
cache key: `drawings:v1`

interface DrawingsCacheV1 {
  version: 1
  drawings: Drawing[]
  savedAt: string // ISO
}
```

- Validate atomically; discard corrupt blob.
- `DrawingsRoot`: hydrate → `drawingStore.hydrate(drawings)`.
- On every successful mutation, debounce 100–200 ms write of full array.
- No per-symbol keys (simpler; filter in memory).

### 2.10 Files to add / touch

**Add:**

| Path | Role |
|---|---|
| `types/drawing.ts` | Union types |
| `constants/drawings.ts` | Keys, defaults, tool meta |
| `services/drawingCache.ts` | IndexedDB R/W + validation |
| `stores/drawingStore.ts` | Zustand |
| `hooks/useDrawings.ts` | Filtered selector helper |
| `hooks/useDrawingInteraction.ts` | Clicks |
| `hooks/useDrawingKeyboard.ts` | Shortcuts |
| `utils/drawingGeometry.ts` | Normalize rect, R:R, hit-test |
| `components/Drawings/DrawingToolbar.tsx` | UI |
| `components/Drawings/DrawingsLayer.tsx` | Render |
| `components/Drawings/DrawingsRoot.tsx` | Persist/hydrate |
| `*.test.ts(x)` | Coverage |

**Touch:**

| Path | Change |
|---|---|
| `AppShell.tsx` | Mount `DrawingsRoot` |
| `IndicatorsBar.tsx` or `Topbar.tsx` | Mount toolbar |
| `ChartContainer.tsx` | Mount layer + hooks |
| `ChartContainer.test.tsx` | Mock new hooks / layer if needed |
| `ROADMAP.md` / `FE_PHASE_5_HLD.md` | Status (Agent H) |

## 3. Persistence and Database

### 3.1 Server database

**No changes.** Agent D confirms absence of required drawing sync for MVP.

### 3.2 Browser

IndexedDB via `idb-keyval`, same pattern as watchlist cache.

## 4. API / Contracts

None. No OpenAPI changes.

## 5. Testing plan

| Area | Tests |
|---|---|
| Store | add/update/remove/filter/select/tool/draft; hex color retained |
| Cache | round-trip; reject corrupt; version mismatch |
| Geometry | rect normalize; R:R; hit-test thresholds |
| Keyboard | shortcuts; editable guard; Esc precedence |
| Toolbar | tool buttons set activeTool |
| Interaction / layer | smoke with mocked chart APIs |
| Regression | existing App / Chart / Replay / Watchlist suites still green |

## 6. Non-regression constraints

- Do not change watchlist bootstrap or replay session state machines except Esc precedence documented above.
- Do not block `pick_anchor` click handler.
- Do not introduce server calls.

## 7. Open questions → resolved in answers.md

See `questions.md` / `answers.md`. Design above incorporates B2 resolutions.
