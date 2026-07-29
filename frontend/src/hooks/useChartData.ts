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
