import { describe, expect, it } from 'vitest'
import { isRangedFallbackResponse } from '@/utils/chartDataWindow'
import { ChunkManager } from '@/services/chunkManager'

describe('isRangedFallbackResponse', () => {
  it('detects empty and filledFromLatest flags', () => {
    expect(
      isRangedFallbackResponse(100, 200, { candles: [], empty: true }),
    ).toBe(true)
    expect(
      isRangedFallbackResponse(100, 200, {
        candles: [{ time: 900 }],
        filledFromLatest: true,
      }),
    ).toBe(true)
  })

  it('detects non-overlapping bars as fallback', () => {
    expect(
      isRangedFallbackResponse(100, 200, {
        candles: [{ time: 1000 }, { time: 1100 }],
      }),
    ).toBe(true)
    expect(
      isRangedFallbackResponse(100, 200, {
        candles: [{ time: 150 }, { time: 180 }],
      }),
    ).toBe(false)
  })
})

describe('ChunkManager coverage', () => {
  it('hasCoverage matches returned data.start not request start', () => {
    const manager = new ChunkManager()
    manager.addChunk(150, {
      candles: [
        {
          time: 150,
          open: 1,
          high: 1,
          low: 1,
          close: 1,
          volume: 1,
        },
        {
          time: 180,
          open: 1,
          high: 1,
          low: 1,
          close: 1,
          volume: 1,
        },
      ],
      indicators: {},
    })
    expect(manager.hasChunk(100)).toBe(false)
    expect(manager.hasCoverage(100, 200)).toBe(true)
  })
})
