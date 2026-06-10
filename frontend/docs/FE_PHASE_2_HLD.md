# FE Phase 2 High Level Design — Indicators

**Status:** In progress (~90%)  
**Prerequisite:** [FE Phase 1](FE_PHASE_1_HLD.md)  
**Spec:** [SPEC-001 §4.1, §5.2](SPEC-001.md)  
**Decisions:** D-81 (indicators bundled in chart-data)  
**Roadmap:** [ROADMAP.md — Phase 2](ROADMAP.md#phase-2--indicators)

---

## Phase 2 Goal

Render overlay indicators (EMA, SMA) on the main pane and oscillators (RSI, MACD) in
sub-panes — all data from `ChartDataResponse.indicators`, never computed client-side.

---

## What Gets Built

| Area | Files | Status |
|---|---|---|
| Types | `types/indicator.ts` — `IndicatorSpec`, `IndicatorSeriesMap`, catalog types | Done |
| ID util | `utils/indicatorId.ts` — mirrors backend `indicator_series_id` | Done |
| API | `chartDataAdapter` — `indicators` query param, `fetchIndicatorCatalog()` | Done |
| Store | `stores/indicatorStore.ts` — active configs, MACD bundle, `getSpecs()` | Done |
| Chunk merge | `services/chunkManager.ts` — candle + indicator chunk merge | Done |
| Hooks | `useChartData`, `useChunkManager`, `useIndicatorCatalog` | Done |
| Overlay | `components/Indicators/OverlayIndicatorSeries.tsx` | Done |
| Sub-pane | `components/Indicators/IndicatorSubPane.tsx` — synced separate chart | Done |
| Picker UI | `components/Indicators/IndicatorPanel.tsx` | Done |
| Topbar | `components/Layout/IndicatorsBar.tsx` — + Add, chips, remove | Done |
| Wiring | `components/Chart/ChartContainer.tsx` — overlay + sub-panes | Done |

**Indicator query example:**

```
GET /chart-data?...&indicators=[{"key":"EMA","params":{"period":20},"pane":"overlay"}]
→ indicators: { "EMA_20": [{ time, value }], ... }
```

---

## Architecture Notes

- **Overlay vs sub-pane:** EMA/SMA → line series on main price scale; RSI/MACD → separate
  `createChart` instances synced to main time scale (lw-charts v4.2 has no `addPane()`).
- **MACD:** Three series per sub-pane — `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST` (histogram).
- **Chunk merge:** When prepending candles, indicator arrays merge by timestamp in lockstep.
- **Toggle:** Removing an indicator drops it from `indicatorStore` and the next `chart-data`
  request omits it from the `indicators` param.
- **Series IDs:** Built via sorted param keys (e.g. MACD `{fast:12, slow:26, signal:9}` →
  `MACD_LINE_12_9_26`).

---

## Done Criteria

Phase 2 is **complete** when:

- [x] Indicator catalog loads in `IndicatorPanel`
- [ ] Adding EMA(20) renders overlay aligned to candles *(needs live smoke test)*
- [ ] Adding RSI(14) opens sub-pane with correct scale *(needs live smoke test)*
- [x] Removing indicator hides series and stops requesting it
- [x] Scroll-back keeps indicator alignment (chunk merge by timestamp)
- [x] No separate `/indicators/compute` calls for the same view

---

## References

- [SPEC-001.md](SPEC-001.md)
- [FE_PHASE_1_HLD.md](FE_PHASE_1_HLD.md)
- [backend/docs/PHASE_4B_FE_GAPS.md](../../backend/docs/PHASE_4B_FE_GAPS.md)
