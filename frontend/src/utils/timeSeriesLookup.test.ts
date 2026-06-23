import { describe, expect, it } from 'vitest'
import { createTimeLookup, lookupByTime } from '@/utils/timeSeriesLookup'

describe('timeSeriesLookup', () => {
  it('keeps the latest item for duplicate timestamps', () => {
    const lookup = createTimeLookup([
      { time: 100, close: 10 },
      { time: 100, close: 11 },
      { time: 200, close: 20 },
    ])

    expect(lookupByTime(lookup, 100)).toEqual({ time: 100, close: 11 })
    expect(lookupByTime(lookup, 200)).toEqual({ time: 200, close: 20 })
  })

  it('ignores invalid timestamps', () => {
    const lookup = createTimeLookup([
      { time: Number.NaN, value: 10 },
      { time: 100, value: 20 },
    ])

    expect(lookupByTime(lookup, Number.NaN)).toBeNull()
    expect(lookupByTime(lookup, 100)).toEqual({ time: 100, value: 20 })
  })
})
