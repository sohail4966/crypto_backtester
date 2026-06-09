export interface OHLCVBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface CandleDataRange {
  symbolId: string
  timeframe: string
  earliest: number | null
  latest: number | null
  barCount: number
}
