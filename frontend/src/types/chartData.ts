import type { OHLCVBar } from '@/types/candle'
import type { IndicatorSpec, IndicatorSeriesMap } from '@/types/indicator'
import type { Symbol } from '@/types/symbol'

export interface ChartDataRequest {
  symbolId: string
  timeframe: string
  start: number
  end: number
  limit?: number
  indicators?: IndicatorSpec[]
}

export interface ChartDataResponse {
  symbol: Symbol
  timeframe: string
  start: number
  end: number
  candles: OHLCVBar[]
  indicators: IndicatorSeriesMap
  signals: unknown[]
  trades: unknown[]
  nextStart?: number | null
}
