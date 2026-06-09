import type { OHLCVBar } from '@/types/candle'
import type { Symbol } from '@/types/symbol'

export interface ChartDataRequest {
  symbolId: string
  timeframe: string
  start: number
  end: number
  limit?: number
}

export interface ChartDataResponse {
  symbol: Symbol
  timeframe: string
  start: number
  end: number
  candles: OHLCVBar[]
  indicators: Record<string, unknown[]>
  signals: unknown[]
  trades: unknown[]
  nextStart?: number | null
}
