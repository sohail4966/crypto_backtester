# FE Phase 1 High Level Design — Core Chart

**Status:** Complete  
**Prerequisite:** [FE Phase 0](FE_PHASE_0_HLD.md), [backend Phase 4b](../../backend/docs/PHASE_4B_HLD.md) ✅  
**Enables:** FE Phases 2–6  
**Spec:** [SPEC-001 §4.1–4.3, §5.1, §7.1](SPEC-001.md)  
**Decisions:** D-81 (unified chart-data), D-82 (windowed chunks), D-86 (symbol entities)  
**Roadmap:** [ROADMAP.md — Phase 1](ROADMAP.md#phase-1--core-chart)

---

## Phase 1 Goal

Render a candlestick + volume chart for a structured `Symbol`, with windowed chunk loading
and symbol/timeframe switching. Initial window is anchored on **stored data range**, not
wall-clock time.

---

## What Gets Built

| Area | Files |
|---|---|
| Types | `types/symbol.ts`, `types/chartData.ts`, `types/candle.ts` |
| API | `services/chartDataAdapter.ts` — `fetchChartData`, `getCandleDataRange` |
| Windowing | `services/chunkManager.ts`, `hooks/useChunkManager.ts`, `hooks/useChartData.ts` |
| Store | `stores/chartStore.ts` |
| Chart | `components/Chart/ChartContainer.tsx`, `CandlestickSeries.tsx`, `VolumeSeries.tsx`, `ChartContext.tsx` |
| UI | `components/Watchlist/SymbolSearch.tsx`, timeframe selector in `Topbar` |
| Page | `pages/ChartPage.tsx` — wires store + chart + search |
| Utils | `utils/time.ts` — `chartWindowFromDataRange(latest, chunkSize)` |

**Backend endpoints:**

```
GET /api/v1/chart-data?symbolId=&timeframe=&start=&end=&indicators=
GET /api/v1/symbols/search?q=
GET /api/v1/symbols/{id}/data-range?timeframe=
```

---

## Architecture Overview

```
ChartPage
  └── ChartContainer (lw-charts IChartApi, ResizeObserver)
        ├── CandlestickSeries  ◄── useChunkManager assembled bars
        └── VolumeSeries
              ▲
useChunkManager ──► fetchChartData (React Query prefetch)
              ◄── VisibleLogicalRangeChange (scroll-back prefetch)
chartStore ──► Symbol entity, timeframe
```

**Chunk constants (SPEC-001 §4.2):**

| Constant | Value |
|---|---|
| `CHUNK_SIZE_BARS` | 500 |
| `LOOKBACK_CHUNKS` | 2 |
| `LOOKAHEAD_CHUNKS` | 1 |
| `PREFETCH_THRESHOLD` | 0.2 |

---

## Key Engineering Notes

1. **Data-range anchoring:** Call `GET /symbols/{id}/data-range` before first fetch; set
   `end = latest`, `start = latest - chunkDuration`. Do not use `Date.now()` as `end`.
2. **lw-charts colors:** Resolve CSS variables to hex (`resolveChartColor`) before
   `applyOptions` — lw-charts cannot parse `var(--color-*)`.
3. **Chart lifecycle:** Init `IChartApi` once per pane; `useEffect` deps = `[paneId]` only.
   Handlers via refs to avoid destroy/recreate on re-render.
4. **Chunk manager stability:** Stable query keys (`symbolId`, `timeframe`); generation
   counter for in-flight requests — avoid cancel-on-cleanup blanking the chart.
5. **Prepend vs update:** Scroll-back → `series.setData(merged)`; live/replay right-edge
   → `series.update(bar)`.
6. **autoSize:** Set `autoSize: false`; size via `ResizeObserver` + `applyOptions({ width, height })`.

---

## Done Criteria

Phase 1 is **complete** when:

- [x] Chart loads ~500 bars for BTC/USDT `1h` on first paint
- [x] SOL/USDT `1m` loads (data anchored on DB `latest`, not empty window)
- [x] Symbol search returns structured `Symbol[]`; selection updates chart
- [x] Timeframe change refetches with correct window
- [x] Scroll-left prefetches prior chunk without blanking chart
- [x] Volume histogram renders below candles
- [x] `npm run build` passes; manual smoke on synced backend DB

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4B_HLD.md](../../backend/docs/PHASE_4B_HLD.md)
- [PHASE_4B_FE_GAPS.md](../../backend/docs/PHASE_4B_FE_GAPS.md) — backend fixes to remove FE workarounds
- [openapi.yaml](../../backend/docs/openapi.yaml)
