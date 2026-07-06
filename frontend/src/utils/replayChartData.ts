import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap } from '@/types/indicator'

export function filterCandlesBefore(time: number, candles: OHLCVBar[]): OHLCVBar[] {
  return candles.filter((bar) => bar.time < time)
}

export function filterIndicatorsBefore(
  anchor: number,
  indicators: IndicatorSeriesMap,
): IndicatorSeriesMap {
  const next: IndicatorSeriesMap = {}
  for (const [seriesId, points] of Object.entries(indicators)) {
    const filtered = points.filter((point) => point.time < anchor)
    if (filtered.length > 0) {
      next[seriesId] = filtered
    }
  }
  return next
}

export function filterIndicatorsFrom(
  anchor: number,
  indicators: Record<string, IndicatorPoint[]>,
): IndicatorSeriesMap {
  const next: IndicatorSeriesMap = {}
  for (const [seriesId, points] of Object.entries(indicators)) {
    const filtered = points.filter((point) => point.time >= anchor)
    if (filtered.length > 0) {
      next[seriesId] = filtered
    }
  }
  return next
}

export function mergeReplayIndicators(
  baseline: IndicatorSeriesMap,
  revealed: IndicatorSeriesMap,
): IndicatorSeriesMap {
  const next: IndicatorSeriesMap = { ...baseline }
  for (const [seriesId, points] of Object.entries(revealed)) {
    const existing = next[seriesId] ?? []
    const byTime = new Map(existing.map((point) => [point.time, point]))
    for (const point of points) {
      byTime.set(point.time, point)
    }
    next[seriesId] = [...byTime.values()].sort((a, b) => a.time - b.time)
  }
  return next
}

export function composeReplayCandles(
  replaySessionActive: boolean,
  liveCandles: OHLCVBar[],
  baselineCandles: OHLCVBar[],
  revealedCandles: OHLCVBar[],
): OHLCVBar[] {
  if (baselineCandles.length > 0 || revealedCandles.length > 0) {
    return [...baselineCandles, ...revealedCandles]
  }
  if (!replaySessionActive) {
    return liveCandles
  }
  return liveCandles
}
