import { describe, expect, it } from 'vitest'
import { FIT_RIGHT_OFFSET_BARS, FIT_VISIBLE_BARS } from '@/constants/chart'
import { visibleBarsRange } from '@/utils/chartViewport'

describe('visibleBarsRange', () => {
  it('returns null for empty data', () => {
    expect(visibleBarsRange(0)).toBeNull()
  })

  it('shows all bars when total is below the fit limit', () => {
    expect(visibleBarsRange(50)).toEqual({
      from: 0 - FIT_RIGHT_OFFSET_BARS,
      to: 49 + FIT_RIGHT_OFFSET_BARS,
    })
  })

  it('shows the last FIT_VISIBLE_BARS candles anchored to the right', () => {
    const range = visibleBarsRange(500)
    expect(range).toEqual({
      from: 500 - FIT_VISIBLE_BARS - FIT_RIGHT_OFFSET_BARS,
      to: 499 + FIT_RIGHT_OFFSET_BARS,
    })
  })
})
