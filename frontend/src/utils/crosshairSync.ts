import type { IChartApi, ISeriesApi, SeriesType, UTCTimestamp } from 'lightweight-charts'
import type { OHLCVBar } from '@/types/candle'

export function candleCloseAtTime(candles: OHLCVBar[], time: number): number | null {
  const bar = candles.find((row) => row.time === time)
  return bar?.close ?? null
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
