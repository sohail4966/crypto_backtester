import { MACD_KEYS, type IndicatorSpec } from '@/types/indicator'

/** Mirror backend `indicator_series_id` in chart_data_service.py. */
export function indicatorSeriesId(key: string, params: Record<string, unknown>): string {
  const indicator = key.toUpperCase()
  if (Object.keys(params).length === 0) {
    return indicator
  }
  if (Object.keys(params).length === 1 && 'period' in params) {
    return `${indicator}_${params.period}`
  }
  const parts = Object.keys(params)
    .sort()
    .map((name) => String(params[name]))
  return `${indicator}_${parts.join('_')}`
}

export function serializeIndicatorSpecs(specs: IndicatorSpec[]): string {
  return JSON.stringify(
    specs.map((spec) => ({
      key: spec.key,
      params: spec.params,
      ...(spec.pane ? { pane: spec.pane } : {}),
    })),
  )
}

export function specsCacheKey(specs: IndicatorSpec[]): string {
  if (specs.length === 0) {
    return 'none'
  }
  return serializeIndicatorSpecs(
    [...specs].sort((a, b) => {
      const idA = indicatorSeriesId(a.key, a.params)
      const idB = indicatorSeriesId(b.key, b.params)
      return idA.localeCompare(idB)
    }),
  )
}

export function macdSpecs(params: Record<string, unknown>): IndicatorSpec[] {
  return MACD_KEYS.map((key) => ({ key, params, pane: 'subchart' as const }))
}
