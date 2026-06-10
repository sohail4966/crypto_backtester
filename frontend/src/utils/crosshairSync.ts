import type { OHLCVBar } from '@/types/candle'

export function candleCloseAtTime(candles: OHLCVBar[], time: number): number | null {
  const bar = candles.find((row) => row.time === time)
  return bar?.close ?? null
}
