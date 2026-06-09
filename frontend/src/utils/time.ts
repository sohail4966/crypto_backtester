import type { CandleDataRange } from '@/types/candle'

const TIMEFRAME_SECONDS: Record<string, number> = {
  '1m': 60,
  '3m': 3 * 60,
  '5m': 5 * 60,
  '15m': 15 * 60,
  '30m': 30 * 60,
  '1h': 60 * 60,
  '2h': 2 * 60 * 60,
  '4h': 4 * 60 * 60,
  '1d': 24 * 60 * 60,
  '1w': 7 * 24 * 60 * 60,
  '1M': 30 * 24 * 60 * 60,
}

export function timeframeSeconds(timeframe: string): number {
  const seconds = TIMEFRAME_SECONDS[timeframe]
  if (!seconds) {
    throw new Error(`Unsupported timeframe: ${timeframe}`)
  }
  return seconds
}

export function shiftUnixByBars(ts: number, timeframe: string, bars: number): number {
  return ts - bars * timeframeSeconds(timeframe)
}

/**
 * Compute the chart-data request window from stored metadata.
 * Returns null when no anchor timestamp is available.
 */
export function chartWindowFromDataRange(
  range: CandleDataRange,
  chunkSize: number,
  timeframe: string,
): { start: number; end: number } | null {
  if (range.latest == null) {
    return null
  }

  const end = range.latest
  const span = (chunkSize - 1) * timeframeSeconds(timeframe)
  let start = end - span

  if (range.earliest != null) {
    start = Math.max(start, range.earliest)
  }

  return { start, end }
}
