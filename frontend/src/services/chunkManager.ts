import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap } from '@/types/indicator'

export interface ChartChunkPayload {
  candles: OHLCVBar[]
  indicators: IndicatorSeriesMap
}

/**
 * In-memory windowed candle + indicator buffer (D-82).
 *
 * Chunks are keyed by returned data `start` (first bar time). Prefetch guards
 * use coverage checks so request `priorStart` ≠ response `start` does not thrash.
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

  /** True if any stored chunk overlaps the requested [start, end] window. */
  hasCoverage(start: number, end: number): boolean {
    for (const bars of this.candleChunks.values()) {
      if (bars.length === 0) {
        continue
      }
      const chunkStart = bars[0]!.time
      const chunkEnd = bars[bars.length - 1]!.time
      if (chunkStart <= end && chunkEnd >= start) {
        return true
      }
    }
    return false
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

  /** Upsert a live bar into the newest chunk (or create a live chunk). */
  upsertLiveBar(bar: OHLCVBar): void {
    let targetStart: number | null = null
    let latestEnd = -Infinity
    for (const [chunkStart, bars] of this.candleChunks.entries()) {
      const end = bars[bars.length - 1]?.time ?? chunkStart
      if (end >= latestEnd) {
        latestEnd = end
        targetStart = chunkStart
      }
    }

    if (targetStart == null) {
      this.candleChunks.set(bar.time, [bar])
      this.indicatorChunks.set(bar.time, {})
      return
    }

    const bars = [...(this.candleChunks.get(targetStart) ?? [])]
    const last = bars[bars.length - 1]
    if (last && last.time === bar.time) {
      bars[bars.length - 1] = bar
    } else if (!last || bar.time > last.time) {
      bars.push(bar)
    } else {
      const idx = bars.findIndex((b) => b.time === bar.time)
      if (idx >= 0) {
        bars[idx] = bar
      } else {
        bars.push(bar)
        bars.sort((a, b) => a.time - b.time)
      }
    }
    this.candleChunks.set(targetStart, bars)
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
