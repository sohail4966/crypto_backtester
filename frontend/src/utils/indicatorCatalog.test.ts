import { describe, expect, it } from 'vitest'
import { paramFieldDefs, primaryBundleKey } from '@/utils/indicatorCatalog'
import type { IndicatorCatalogEntry } from '@/types/indicator'

describe('indicatorCatalog', () => {
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

  it('builds float param fields for std dev', () => {
    const entry: IndicatorCatalogEntry = {
      key: 'BB_UPPER',
      inputs: ['close'],
      sharedParams: ['period', 'std'],
      defaultParams: { period: 20, std: 2 },
      pane: 'overlay',
    }
    const stdField = paramFieldDefs(entry).find((field) => field.name === 'std')
    expect(stdField?.type).toBe('float')
  })
})
