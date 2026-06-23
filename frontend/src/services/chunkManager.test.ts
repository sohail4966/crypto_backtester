import { describe, expect, it } from 'vitest'
import { ChunkManager } from '@/services/chunkManager'
import type { OHLCVBar } from '@/types/candle'

function bar(time: number, close = time): OHLCVBar {
  return {
    time,
    open: close - 1,
    high: close + 1,
    low: close - 2,
    close,
    volume: close * 10,
  }
}

describe('ChunkManager', () => {
  it('dedupes overlapping candle and indicator points by timestamp', () => {
    const manager = new ChunkManager()

    manager.addChunk(100, {
      candles: [bar(100, 10), bar(200, 20)],
      indicators: {
        EMA_20: [
          { time: 100, value: 11 },
          { time: 200, value: 21 },
        ],
      },
    })
    manager.addChunk(200, {
      candles: [bar(200, 22), bar(300, 30)],
      indicators: {
        EMA_20: [
          { time: 200, value: 23 },
          { time: 300, value: 31 },
        ],
      },
    })

    expect(manager.getAssembledCandles()).toEqual([bar(100, 10), bar(200, 22), bar(300, 30)])
    expect(manager.getAssembledIndicators()).toEqual({
      EMA_20: [
        { time: 100, value: 11 },
        { time: 200, value: 23 },
        { time: 300, value: 31 },
      ],
    })
  })

  it('clears stale indicators when an existing chunk is replaced with an empty indicator map', () => {
    const manager = new ChunkManager()

    manager.addChunk(100, {
      candles: [bar(100, 10)],
      indicators: {
        EMA_20: [{ time: 100, value: 11 }],
      },
    })
    manager.addChunk(100, {
      candles: [bar(100, 12)],
      indicators: {},
    })

    expect(manager.getAssembledCandles()).toEqual([bar(100, 12)])
    expect(manager.getAssembledIndicators()).toEqual({})
  })

  it('evicts candles and indicators outside the lookback window', () => {
    const manager = new ChunkManager()

    manager.addChunk(100, {
      candles: [bar(100, 10), bar(200, 20)],
      indicators: { EMA_20: [{ time: 100, value: 11 }] },
    })
    manager.addChunk(300, {
      candles: [bar(300, 30)],
      indicators: { EMA_20: [{ time: 300, value: 31 }] },
    })

    expect(manager.evictBefore(250)).toBe(true)
    expect(manager.getAssembledCandles()).toEqual([bar(300, 30)])
    expect(manager.getAssembledIndicators()).toEqual({
      EMA_20: [{ time: 300, value: 31 }],
    })
  })
})
