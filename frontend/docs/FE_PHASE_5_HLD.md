# FE Phase 5 High Level Design — Drawings (MVP)

**Status:** Implemented (v1)  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md)  
**Spec:** [SPEC-001 §5.5–5.6](SPEC-001.md)  
**Decisions:** D-83 (MVP tool scope), D-84 (Price Range primitive), D-85 (IndexedDB until 4d)  
**Roadmap:** [ROADMAP.md — Phase 5](ROADMAP.md#phase-5--drawings-mvp)

---

## Phase 5 Goal

Five drawing tools on the chart with per-symbol/timeframe persistence in IndexedDB. Price
Range is a first-class primitive with entry / target / stop levels and R:R display.

---

## What Gets Built

| Area | Files |
|---|---|
| Types | `types/drawing.ts` — `Drawing` union (SPEC-001 §5.5) |
| Store | `stores/drawingStore.ts` — tools, CRUD, IndexedDB persist |
| UI | `DrawingToolbar.tsx` |
| Render | `DrawingsLayer.tsx` — price lines, rectangles, HTML overlay for labels |
| Hooks | `hooks/useDrawings.ts` — filter by `symbolId` + `timeframe` |
| Utils | `utils/color.ts` — `resolveChartColor()` for lw-charts |

**MVP tools:**

| Tool | Type key |
|---|---|
| Trend Line | `trend_line` |
| Horizontal Line | `horizontal_line` |
| Rectangle | `rectangle` |
| Price Range | `price_range` |
| Text Note | `text_note` |

**Excluded (SPEC-002):** Fibonacci, channels, rays, vertical line, brushes.

---

## Interaction Model

1. User selects tool → `drawingStore.setActiveTool(type)`
2. `ChartContainer` attaches `chart.subscribeClick()`
3. First click → draft anchor (local state)
4. Second click → `drawingStore.addDrawing()`; tool clears
5. `DrawingsLayer` re-renders from store subscription

**Price Range:** Three horizontal levels + shaded zone; R:R label via chart
`priceToCoordinate` HTML overlay.

---

## Architecture Notes

- **Colors:** Store resolved hex at creation time; theme toggle does not rewrite stored hex in v1.
- **Zustand selectors:** Select `allDrawings` + `useMemo` filter — avoid `drawingsFor()`
  returning new array every call.
- **Backend sync:** Deferred to Phase 4d; IndexedDB is source of truth for MVP.
- **Drag-edit:** Deferred beyond v1 (select + delete only).

---

## Done Criteria

Phase 5 is **complete** when:

- [x] All five tools create drawings via click-to-place
- [x] Drawings render correctly on chart (lines, rects, price range zones)
- [x] Drawings scoped per `symbolId` + `timeframe`
- [x] Drawings survive page reload (IndexedDB)
- [x] `Esc` cancels active tool; `Delete` removes selected drawing
- [x] No lw-charts color parse errors (`var(--*)` resolved to hex)

---

## References

- [SPEC-001.md](SPEC-001.md)
- Backend Phase 4d (future workspace sync)
- Pipeline: `docs/agents/fe-phase-5-drawings/`
