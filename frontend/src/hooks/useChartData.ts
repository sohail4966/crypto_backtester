import { useQuery } from '@tanstack/react-query'
import { fetchChartData } from '@/services/chartDataAdapter'
import type { ChartDataRequest } from '@/types/chartData'

/** Stable key for the first paint load — avoids refetch on route remount. */
export function initialChartDataQueryKey(symbolId: string, timeframe: string) {
  return ['chart-data', symbolId, timeframe, 'initial'] as const
}

// Scroll-back chunks include the full window in the key (D-81).
export function chartDataQueryKey(request: ChartDataRequest) {
  return [
    'chart-data',
    request.symbolId,
    request.timeframe,
    request.start,
    request.end,
    request.limit ?? null,
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
