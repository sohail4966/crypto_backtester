import type { IChartApi, ISeriesApi, SeriesType, UTCTimestamp } from 'lightweight-charts'
import type { OHLCVBar } from '@/types/candle'
import { lookupByTime } from '@/utils/timeSeriesLookup'

export function createCandleCloseLookup(candles: readonly OHLCVBar[]): Map<number, number> {
  const byTime = new Map<number, number>()
  for (const candle of candles) {
    if (Number.isFinite(candle.time) && Number.isFinite(candle.close)) {
      byTime.set(candle.time, candle.close)
    }
  }
  return byTime
}

export function candleCloseFromLookup(
  lookup: ReadonlyMap<number, number>,
  time: number,
): number | null {
  return lookupByTime(lookup, time)
}

/** lw-charts throws if the series/chart is mid-mount or the time is not in series data. */
export function safeSetCrosshairPosition(
  chart: IChartApi,
  price: number,
  time: UTCTimestamp,
  series: ISeriesApi<SeriesType>,
): void {
  if (!Number.isFinite(price)) {
    return
  }
  try {
    chart.setCrosshairPosition(price, time, series)
  } catch {
    // Sub-pane may still be mounting or indicator data may not cover this bar yet.
  }
}
