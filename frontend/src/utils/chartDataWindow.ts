/**
 * Detect whether a chart-data response is a silent "latest bars" fallback for a
 * ranged historical request (FE-011). Prefer BE `empty` / `filledFromLatest` when present.
 */
export function isRangedFallbackResponse(
  requestStart: number,
  requestEnd: number,
  data: {
    candles: { time: number }[]
    empty?: boolean
    filledFromLatest?: boolean
    start?: number
  },
): boolean {
  if (data.empty === true || data.filledFromLatest === true) {
    return true
  }
  if (data.candles.length === 0) {
    return true
  }
  const first = data.candles[0]!.time
  const last = data.candles[data.candles.length - 1]!.time
  // No overlap between response bars and requested window → treat as fallback.
  return last < requestStart || first > requestEnd
}
