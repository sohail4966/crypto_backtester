import { useQuery } from '@tanstack/react-query'
import { fetchChartData } from '@/services/chartDataAdapter'
import type { ChartDataRequest } from '@/types/chartData'
import type { IndicatorSpec } from '@/types/indicator'
import { specsCacheKey } from '@/utils/indicatorId'

/** Stable key for the first paint load — includes indicator specs when active. */
export function initialChartDataQueryKey(
  symbolId: string,
  timeframe: string,
  indicatorSpecs: IndicatorSpec[] = [],
) {
  return [
    'chart-data',
    symbolId,
    timeframe,
    'initial',
    specsCacheKey(indicatorSpecs),
  ] as const
}

export function chartDataQueryKey(request: ChartDataRequest) {
  return [
    'chart-data',
    request.symbolId,
    request.timeframe,
    request.start,
    request.end,
    request.limit ?? null,
    specsCacheKey(request.indicators ?? []),
  ] as const
}

export function useChartData(request: ChartDataRequest | null, enabled = true) {
  return useQuery({
    queryKey: request ? chartDataQueryKey(request) : ['chart-data', 'idle'],
    queryFn: () => {
      if (!request) {
        throw new Error('Chart data request is required')
      }
      return fetchChartData(request)
    },
    enabled: enabled && request != null,
    staleTime: 60_000,
  })
}
