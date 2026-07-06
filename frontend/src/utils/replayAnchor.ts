import type { OHLCVBar } from '@/types/candle'

/** Snap a chart click time to the nearest loaded bar open time. */
export function snapToNearestBarTime(clickedTime: number, candles: OHLCVBar[]): number {
  if (candles.length === 0) {
    return clickedTime
  }

  let best = candles[0].time
  let bestDist = Math.abs(clickedTime - best)
  for (const bar of candles) {
    const dist = Math.abs(clickedTime - bar.time)
    if (dist < bestDist) {
      best = bar.time
      bestDist = dist
    }
  }
  return best
}
