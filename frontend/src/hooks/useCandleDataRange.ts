import { useQuery } from '@tanstack/react-query'
import { getCandleDataRange } from '@/services/chartDataAdapter'

export function candleDataRangeQueryKey(symbolId: string, timeframe: string) {
  return ['candle-data-range', symbolId, timeframe] as const
}

export function useCandleDataRange(symbolId: string | undefined, timeframe: string) {
  return useQuery({
    queryKey: candleDataRangeQueryKey(symbolId ?? '', timeframe),
    queryFn: () => getCandleDataRange(symbolId!, timeframe),
    enabled: Boolean(symbolId),
    staleTime: 60_000,
  })
}
