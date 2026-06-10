import { describe, expect, it } from 'vitest'
import { bundleGroupKey, paramFieldDefs, primaryBundleKey } from '@/utils/indicatorCatalog'
import type { IndicatorCatalogEntry } from '@/types/indicator'

describe('indicatorCatalog', () => {
  it('groups bundle siblings under one key', () => {
    const params = { period: 20, std: 2 }
    expect(bundleGroupKey('BB_UPPER', params)).toBe(bundleGroupKey('BB_LOWER', params))
    expect(bundleGroupKey('MACD_LINE', { fast: 12, slow: 26, signal: 9 })).toBe(
      bundleGroupKey('MACD_HIST', { fast: 12, slow: 26, signal: 9 }),
    )
  })

  it('resolves primary bundle key for siblings', () => {
    expect(primaryBundleKey('STOCH_D')).toBe('STOCH_K')
    expect(primaryBundleKey('EMA')).toBeNull()
  })

  it('builds param fields from shared params', () => {
    const entry: IndicatorCatalogEntry = {
      key: 'MACD_LINE',
      inputs: ['close'],
      sharedParams: ['fast', 'slow', 'signal'],
      defaultParams: { fast: 12, slow: 26, signal: 9 },
      pane: 'subchart',
    }
    expect(paramFieldDefs(entry).map((field) => field.name)).toEqual(['fast', 'slow', 'signal'])
  })
})
