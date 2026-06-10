import { describe, expect, it } from 'vitest'
import { indicatorSeriesId } from '@/utils/indicatorId'

describe('indicatorSeriesId', () => {
  it('builds period suffix', () => {
    expect(indicatorSeriesId('EMA', { period: 20 })).toBe('EMA_20')
  })

  it('builds multi-param suffix', () => {
    expect(indicatorSeriesId('MACD_LINE', { fast: 12, slow: 26, signal: 9 })).toBe(
      'MACD_LINE_12_9_26',
    )
  })
})
