import { describe, expect, it } from 'vitest'
import { defaultBundleSeriesColor } from '@/utils/indicatorDisplay'

describe('indicatorDisplay bundle defaults', () => {
  it('assigns distinct default colors for Bollinger band lines', () => {
    const upper = defaultBundleSeriesColor('BB_UPPER', 0)
    const middle = defaultBundleSeriesColor('BB_MIDDLE', 1)
    const lower = defaultBundleSeriesColor('BB_LOWER', 2)
    expect(new Set([upper, middle, lower]).size).toBe(3)
  })
})
