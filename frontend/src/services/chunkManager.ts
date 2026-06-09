import type { OHLCVBar } from '@/types/candle'

/**
 * In-memory windowed candle buffer (D-82).
 *
 * Chunks are keyed by request `start` time. Scroll-back prepends overlap at chunk
 * boundaries, so assembly dedupes by bar timestamp before handing data to lw-charts.
 */
export class ChunkManager {
  private readonly chunks = new Map<number, OHLCVBar[]>()

  reset(): void {
    this.chunks.clear()
  }

  hasChunk(chunkStart: number): boolean {
    return this.chunks.has(chunkStart)
  }

  addChunk(chunkStart: number, bars: OHLCVBar[]): void {
    if (bars.length === 0) {
      return
    }
    this.chunks.set(chunkStart, bars)
  }

  getAssembled(): OHLCVBar[] {
    // lw-charts requires a single sorted array for prepends — merge + dedupe here.
    const byTime = new Map<number, OHLCVBar>()
    for (const bars of this.chunks.values()) {
      for (const bar of bars) {
        byTime.set(bar.time, bar)
      }
    }
    return [...byTime.values()].sort((a, b) => a.time - b.time)
  }

  getEarliestTime(): number | null {
    const assembled = this.getAssembled()
    return assembled[0]?.time ?? null
  }

  /** Drop chunks that fall outside the look-back window to bound memory use. */
  evictBefore(cutoffTime: number): boolean {
    let evicted = false
    for (const [chunkStart, bars] of this.chunks.entries()) {
      const chunkEnd = bars[bars.length - 1]?.time ?? chunkStart
      if (chunkEnd < cutoffTime) {
        this.chunks.delete(chunkStart)
        evicted = true
      }
    }
    return evicted
  }
}
