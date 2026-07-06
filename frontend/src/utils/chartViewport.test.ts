import { describe, expect, it, vi } from 'vitest'
import {
  captureVisibleTimeRange,
  restoreVisibleTimeRange,
} from '@/utils/chartViewport'

describe('chartViewport time range', () => {
  it('captures numeric visible time ranges', () => {
    const chart = {
      timeScale: () => ({
        getVisibleRange: () => ({ from: 100, to: 200 }),
        setVisibleRange: vi.fn(),
      }),
    }

    expect(captureVisibleTimeRange(chart as never)).toEqual({ from: 100, to: 200 })
  })

  it('restores a captured range on the chart', () => {
    const setVisibleRange = vi.fn()
    const chart = {
      timeScale: () => ({
        getVisibleRange: () => null,
        setVisibleRange,
      }),
    }

    restoreVisibleTimeRange(chart as never, { from: 100 as never, to: 200 as never })
    expect(setVisibleRange).toHaveBeenCalledWith({ from: 100, to: 200 })
  })
})
