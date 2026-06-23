/**
 * Chart-specific API adapters.
 *
 * All candle loads go through the unified `/chart-data` endpoint (D-81) so candles
 * and (later) indicators share one aligned payload per window.
 */
import { apiRequest } from '@/services/api'
import type { CandleDataRange } from '@/types/candle'
import type { ChartDataRequest, ChartDataResponse } from '@/types/chartData'
import type { IndicatorCatalogEntry } from '@/types/indicator'
import type { Symbol } from '@/types/symbol'
import { normalizeCatalogEntry } from '@/utils/indicatorCatalog'
import { serializeIndicatorSpecs } from '@/utils/indicatorId'

function buildChartDataQuery(request: ChartDataRequest): string {
  const params = new URLSearchParams({
    symbolId: request.symbolId,
    timeframe: request.timeframe,
    start: String(request.start),
    end: String(request.end),
  })

  if (request.limit != null) {
    params.set('limit', String(request.limit))
  }

  if (request.indicators && request.indicators.length > 0) {
    params.set('indicators', serializeIndicatorSpecs(request.indicators))
  }

  return `/chart-data?${params.toString()}`
}

export function fetchChartData(request: ChartDataRequest): Promise<ChartDataResponse> {
  return apiRequest<ChartDataResponse>(buildChartDataQuery(request))
}

export function fetchIndicatorCatalog(): Promise<IndicatorCatalogEntry[]> {
  return apiRequest<Record<string, unknown>[]>('/indicators').then((rows) =>
    rows.map(normalizeCatalogEntry),
  )
}

export function getCandleDataRange(
  symbolId: string,
  timeframe: string,
): Promise<CandleDataRange> {
  const params = new URLSearchParams({ timeframe })
  // Symbol ids contain slashes (e.g. BTC/USDT) — must encode for path segments.
  return apiRequest<CandleDataRange>(
    `/symbols/${encodeURIComponent(symbolId)}/data-range?${params.toString()}`,
  )
}

/**
 * Resolve candle bounds for chart anchoring.
 *
 * Derived timeframes (1h, 4h, …) are aggregated from stored 1m rows — backend
 * data-range often returns null for them even when candles exist. Fall back to
 * 1m metadata for the anchor timestamp.
 */
export async function resolveCandleDataRange(
  symbolId: string,
  timeframe: string,
): Promise<CandleDataRange> {
  const range = await getCandleDataRange(symbolId, timeframe)
  if (range.latest != null || timeframe === '1m') {
    return range
  }

  const base = await getCandleDataRange(symbolId, '1m')
  if (base.latest == null) {
    return range
  }

  return {
    ...range,
    latest: base.latest,
    earliest: range.earliest ?? base.earliest,
  }
}

export function searchSymbols(query = ''): Promise<Symbol[]> {
  const params = new URLSearchParams({ active_only: 'true' })
  if (query) {
    params.set('q', query)
  }
  return apiRequest<Symbol[]>(`/symbols/search?${params.toString()}`)
}

export function getSymbol(symbolId: string): Promise<Symbol> {
  return apiRequest<Symbol>(`/symbols/${encodeURIComponent(symbolId)}`)
}
