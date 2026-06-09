import type { IChartApi } from 'lightweight-charts'
import { FIT_RIGHT_OFFSET_BARS, FIT_VISIBLE_BARS } from '@/constants/chart'

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
