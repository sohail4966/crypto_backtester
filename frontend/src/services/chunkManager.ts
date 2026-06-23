import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap } from '@/types/indicator'

export interface ChartChunkPayload {
  candles: OHLCVBar[]
  indicators: IndicatorSeriesMap
}

/**
 * In-memory windowed candle + indicator buffer (D-82).
 *
 * Chunks are keyed by request `start` time. Scroll-back prepends overlap at chunk
 * boundaries, so assembly dedupes by bar timestamp before handing data to lw-charts.
 */
export class ChunkManager {
  private readonly candleChunks = new Map<number, OHLCVBar[]>()
  private readonly indicatorChunks = new Map<number, IndicatorSeriesMap>()

  reset(): void {
    this.candleChunks.clear()
    this.indicatorChunks.clear()
  }

  hasChunk(chunkStart: number): boolean {
    return this.candleChunks.has(chunkStart)
  }

  addChunk(chunkStart: number, payload: ChartChunkPayload): void {
    if (payload.candles.length === 0) {
      return
    }
    this.candleChunks.set(chunkStart, payload.candles)
    this.indicatorChunks.set(chunkStart, payload.indicators)
  }

  getAssembledCandles(): OHLCVBar[] {
    const byTime = new Map<number, OHLCVBar>()
    for (const bars of this.candleChunks.values()) {
      for (const bar of bars) {
        byTime.set(bar.time, bar)
      }
    }
    return [...byTime.values()].sort((a, b) => a.time - b.time)
  }

  getAssembledIndicators(): IndicatorSeriesMap {
    const bySeries = new Map<string, Map<number, IndicatorPoint>>()
    for (const chunk of this.indicatorChunks.values()) {
      for (const [seriesId, points] of Object.entries(chunk)) {
        const bucket = bySeries.get(seriesId) ?? new Map<number, IndicatorPoint>()
        for (const point of points) {
          bucket.set(point.time, point)
        }
        bySeries.set(seriesId, bucket)
      }
    }

    const assembled: IndicatorSeriesMap = {}
    for (const [seriesId, points] of bySeries.entries()) {
      assembled[seriesId] = [...points.values()].sort((a, b) => a.time - b.time)
    }
    return assembled
  }

  getEarliestTime(): number | null {
    const assembled = this.getAssembledCandles()
    return assembled[0]?.time ?? null
  }

  /** Drop chunks that fall outside the look-back window to bound memory use. */
  evictBefore(cutoffTime: number): boolean {
    let evicted = false
    for (const [chunkStart, bars] of this.candleChunks.entries()) {
      const chunkEnd = bars[bars.length - 1]?.time ?? chunkStart
      if (chunkEnd < cutoffTime) {
        this.candleChunks.delete(chunkStart)
        this.indicatorChunks.delete(chunkStart)
        evicted = true
      }
    }
    return evicted
  }
}
