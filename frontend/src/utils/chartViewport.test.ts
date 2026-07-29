import { describe, expect, it, vi } from 'vitest'
import { fitToVisibleBars, visibleBarsRange } from '@/utils/chartViewport'

describe('chartViewport', () => {
  it('builds a logical range for the last visible bars', () => {
    expect(visibleBarsRange(500, 120, 8)).toEqual({ from: 372, to: 507 })
  })

  it('returns null when there are no bars', () => {
    expect(visibleBarsRange(0)).toBeNull()
  })

  it('fits the chart to the visible bars range', () => {
    const setVisibleLogicalRange = vi.fn()
    const chart = {
      timeScale: () => ({ setVisibleLogicalRange }),
    }

    fitToVisibleBars(chart as never, 500, 120)
    expect(setVisibleLogicalRange).toHaveBeenCalledWith({ from: 372, to: 507 })
  })
})
