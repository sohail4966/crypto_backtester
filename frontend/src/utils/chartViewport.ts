import type { IChartApi, UTCTimestamp } from 'lightweight-charts'
import { FIT_RIGHT_OFFSET_BARS, FIT_VISIBLE_BARS } from '@/constants/chart'

export interface VisibleTimeRange {
  from: UTCTimestamp
  to: UTCTimestamp
}

/** Read the current on-screen time window (stable across bar count changes). */
export function captureVisibleTimeRange(chart: IChartApi | null): VisibleTimeRange | null {
  if (!chart) {
    return null
  }
  const range = chart.timeScale().getVisibleRange()
  if (!range || typeof range.from !== 'number' || typeof range.to !== 'number') {
    return null
  }
  return { from: range.from as UTCTimestamp, to: range.to as UTCTimestamp }
}

/** Restore a previously captured time window after setData. */
export function restoreVisibleTimeRange(
  chart: IChartApi | null,
  range: VisibleTimeRange | null,
): void {
  if (!chart || !range) {
    return
  }
  try {
    chart.timeScale().setVisibleRange(range)
  } catch {
    // Range can be invalid while the series is empty.
  }
}

/** Logical range that shows the last N candles with TradingView-style right padding. */
export function visibleBarsRange(
  totalBars: number,
  visibleBars = FIT_VISIBLE_BARS,
  rightOffset = FIT_RIGHT_OFFSET_BARS,
): { from: number; to: number } | null {
  if (totalBars <= 0) {
    return null
  }

  const count = Math.min(visibleBars, totalBars)
  const lastIndex = totalBars - 1

  return {
    from: lastIndex - count + 1 - rightOffset,
    to: lastIndex + rightOffset,
  }
}

export function fitToVisibleBars(
  chart: IChartApi,
  totalBars: number,
  visibleBars = FIT_VISIBLE_BARS,
): void {
  const range = visibleBarsRange(totalBars, visibleBars)
  if (!range) {
    return
  }

  chart.timeScale().setVisibleLogicalRange(range)
}
