# FE Phase 2 High Level Design — Indicators

**Status:** Not started  
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

| Area | Files |
|---|---|
| Types | `types/indicator.ts` — `IndicatorConfig`, `IndicatorSeriesMap` |
| API | Extend `chartDataAdapter` — serialise `indicators` query param |
| Store | `stores/indicatorStore.ts` — active configs per pane |
| Components | `components/Indicators/IndicatorPanel.tsx`, `OverlayIndicator.tsx`, `IndicatorPane.tsx` |
| Hooks | Extend `useChartData` / `useChunkManager` to include indicator keys in cache key |
| Catalog | `fetchIndicatorCatalog` → `GET /indicators` |

**Indicator query example:**

```
GET /chart-data?...&indicators=EMA_20,RSI_14
→ indicators: { "EMA_20": [...], "RSI_14": [...] }
```

---

## Architecture Notes

- **Overlay vs sub-pane:** EMA/SMA/VWAP → line series on main price scale; RSI/MACD →
  `chart.addPane()` (lw-charts v4).
- **MACD:** Three series per pane — macd line, signal line, histogram.
- **Chunk merge:** When prepending candles, merge indicator arrays by timestamp in lockstep.
- **Toggle:** Disabling an indicator removes its series and drops it from the next
  `chart-data` request.

---

## Done Criteria

Phase 2 is **complete** when:

- [ ] Indicator catalog loads in `IndicatorPanel`
- [ ] Adding EMA(20) renders overlay aligned to candles
- [ ] Adding RSI(14) opens sub-pane with correct scale
- [ ] Removing indicator hides series and stops requesting it
- [ ] Scroll-back keeps indicator alignment (no drift vs candles)
- [ ] No separate `/indicators/compute` calls for the same view

---

## References

- [SPEC-001.md](SPEC-001.md)
- [FE_PHASE_1_HLD.md](FE_PHASE_1_HLD.md)
