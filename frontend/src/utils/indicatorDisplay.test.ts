import { describe, expect, it } from 'vitest'
import { createIndicatorValueLookup, indicatorValueFromLookup } from '@/utils/indicatorDisplay'

describe('indicatorDisplay', () => {
  it('indexes only finite indicator values by timestamp', () => {
    const lookup = createIndicatorValueLookup([
      { time: 100, value: 10 },
      { time: 200, value: null },
      { time: 300, value: Number.NaN },
    ])

    expect(indicatorValueFromLookup(lookup, 100)).toBe(10)
    expect(indicatorValueFromLookup(lookup, 200)).toBeNull()
    expect(indicatorValueFromLookup(lookup, 300)).toBeNull()
  })
})
