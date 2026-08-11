export type StrategyKind = 'dual' | 'long_only'

export interface StrategyInfo {
  name: string
  kind: StrategyKind
}

export interface BacktestMetrics {
  totalReturn: number
  winRate: number
  maxDrawdown: number
  tradeCount: number
  forcedClose: boolean
  finalCapital: number
  initialCapital: number
  sharpeRatio?: number | null
  sortinoRatio?: number | null
  calmarRatio?: number | null
  profitFactor?: number | null
  benchmarkReturn?: number | null
  alphaVsBenchmark?: number | null
}

export interface TradeDetail {
  entryTime: number
  exitTime: number
  entryPrice: number
  exitPrice: number
  side: string
  exitReason: string
  forcedClose: boolean
  returnPct: number
  size: number
  commissionPaid: number
  pnlQuote: number
}

export interface BacktestRun {
  runId: string
  symbol: string
  timeframe: string
  start: number
  end: number
  initialCapital: number
  strategyName: string | null
  status: string
  metrics: BacktestMetrics
  createdAt: string
}

export interface RunBacktestInput {
  symbol: string
  timeframe: string
  start: number
  end: number
  initialCapital?: number
  strategyName: string
}
