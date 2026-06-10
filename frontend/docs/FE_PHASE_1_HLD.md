# FE Phase 1 High Level Design — Core Chart

**Status:** Complete ✅ (signed off 2026-06-10)  
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
| API | `services/chartDataAdapter.ts` — `fetchChartData`, `getCandleDataRange`, `resolveCandleDataRange` |
| Windowing | `services/chunkManager.ts`, `hooks/useChunkManager.ts`, `hooks/useChartData.ts` |
| Store | `stores/chartStore.ts`, `stores/layoutStore.ts` |
| Chart | `components/Chart/ChartContainer.tsx`, `CandlestickSeries.tsx`, `VolumeSeries.tsx`, `ChartContext.tsx`, `ChartLegend.tsx`, `ChartZoomControls.tsx` |
| Layout | `Sidebar.tsx` (nav + timezone + settings), `Topbar.tsx` (symbol, timeframe dropdown, indicators placeholder) |
| UI | `SymbolSearch.tsx`, `TimeframeSelector.tsx`, `TimezoneSelector.tsx`, `ChartSettingsMenu.tsx` |
| Page | `pages/ChartPage.tsx` |
| Utils | `utils/time.ts`, `utils/color.ts`, `utils/chartViewport.ts`, `utils/chartTimezone.ts`, `utils/format.ts` |

**Backend endpoints:**

```
GET /api/v1/chart-data?symbolId=&timeframe=&start=&end=&limit=
GET /api/v1/symbols/search?q=
GET /api/v1/symbols/{id}/data-range?timeframe=
GET /api/v1/symbols/{id}
```

---

## Architecture Overview

```
ChartPage
  └── AppShell
        ├── Sidebar — Chart / Replay / Backtest nav; timezone + chart settings (bottom)
        └── Topbar — symbol search, timeframe dropdown, indicators bar (Phase 2)
              └── ChartContainer (lw-charts, ResizeObserver)
                    ├── CandlestickSeries  ◄── useChunkManager assembled bars
                    ├── VolumeSeries
                    ├── ChartLegend (OHLC + volume on crosshair)
                    └── ChartZoomControls (bottom-centre, auto-hide)
                          ▲
useChunkManager ──► fetchChartData (React Query)
              ◄── VisibleLogicalRangeChange (scroll-back prefetch)
chartStore ──► symbol, timeframe, timezone, showGrid
```

**Chunk constants (SPEC-001 §4.2):**

| Constant | Value |
|---|---|
| `CHUNK_SIZE_BARS` | 500 |
| `LOOKBACK_CHUNKS` | 2 |
| `LOOKAHEAD_CHUNKS` | 1 (constant only; scroll-ahead not implemented) |
| `PREFETCH_THRESHOLD` | 0.2 |
| `FIT_VISIBLE_BARS` | 120 |
| `ZOOM_CONTROLS_AUTO_HIDE_MS` | 2000 |

---

## Key Engineering Notes

1. **Data-range anchoring:** Call `GET /symbols/{id}/data-range` before first fetch; set
   `end = latest`, `start = latest - chunkDuration`. Do not use `Date.now()` as `end`.
2. **Derived timeframe workaround:** `resolveCandleDataRange()` falls back to `1m` metadata
   when `1h`/`4h`/`15m` data-range returns null — see [PHASE_4B_FE_GAPS.md](../../backend/docs/PHASE_4B_FE_GAPS.md).
3. **lw-charts colors:** Resolve CSS variables to hex (`resolveChartColor`) before
   `applyOptions` — lw-charts cannot parse `var(--color-*)`.
4. **Chart lifecycle:** Init `IChartApi` once per pane; `useEffect` deps = `[paneId]` only.
   Handlers via refs to avoid destroy/recreate on re-render.
5. **Chunk manager stability:** Generation counter for in-flight requests; stable query keys;
   `setData` only when chunks change — not on every scroll frame.
6. **Pan/zoom:** `fitContent` once per symbol/timeframe; prefetch only on user scroll-left;
   zoom bar hidden by default (hover or 2s after wheel zoom).
7. **Timezone display:** UTC timestamps formatted via `tickMarkFormatter` / `timeFormatter`
   — data stays UTC; display-only conversion.

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

## Phase 1 Sign-Off Checklist

| Item | Status | Notes |
|---|---|---|
| Core chart-data pipeline | ✅ | Unified endpoint, chunk manager, React Query cache |
| Symbol entity (D-86) | ✅ | `chartStore.symbol.id` used in all API calls |
| Windowed loading (D-82) | ✅ | 500-bar chunks, scroll-back prefetch, eviction |
| UX beyond minimum scope | ✅ | Legend, zoom, timezone, grid toggle, sidebar layout |
| Automated tests | ⚠️ | 13 unit/App tests; no chunkManager integration tests |
| Backend workaround | ⚠️ | Derived TF data-range fallback in FE until Phase 4b.1 |
| Docs match UI | ✅ | Updated 2026-06-10 |

**Overall rating:** ~92% — functionally complete; Phase 2 may proceed.

---

## References

- [SPEC-001.md](SPEC-001.md)
- [PHASE_4B_HLD.md](../../backend/docs/PHASE_4B_HLD.md)
- [PHASE_4B_FE_GAPS.md](../../backend/docs/PHASE_4B_FE_GAPS.md)
- [openapi.yaml](../../backend/docs/openapi.yaml)
