import { apiRequest } from '@/services/api'
import type {
  BacktestMetrics,
  BacktestRun,
  RunBacktestInput,
  StrategyInfo,
  TradeDetail,
} from '@/types/backtest'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function normalizeMetrics(raw: unknown): BacktestMetrics {
  const m = asRecord(raw)
  return {
    totalReturn: asNumber(m.total_return ?? m.totalReturn),
    winRate: asNumber(m.win_rate ?? m.winRate),
    maxDrawdown: asNumber(m.max_drawdown ?? m.maxDrawdown),
    tradeCount: asNumber(m.trade_count ?? m.tradeCount),
    forcedClose: Boolean(m.forced_close ?? m.forcedClose),
    finalCapital: asNumber(m.final_capital ?? m.finalCapital),
    initialCapital: asNumber(m.initial_capital ?? m.initialCapital),
    sharpeRatio: (m.sharpe_ratio ?? m.sharpeRatio) as number | null | undefined,
    sortinoRatio: (m.sortino_ratio ?? m.sortinoRatio) as number | null | undefined,
    calmarRatio: (m.calmar_ratio ?? m.calmarRatio) as number | null | undefined,
    profitFactor: (m.profit_factor ?? m.profitFactor) as number | null | undefined,
    benchmarkReturn: (m.benchmark_return ?? m.benchmarkReturn) as number | null | undefined,
    alphaVsBenchmark: (m.alpha_vs_benchmark ?? m.alphaVsBenchmark) as
      | number
      | null
      | undefined,
  }
}

export function normalizeBacktestRun(raw: unknown): BacktestRun {
  const body = asRecord(raw)
  return {
    runId: asString(body.run_id ?? body.runId),
    symbol: asString(body.symbol),
    timeframe: asString(body.timeframe),
    start: asNumber(body.start),
    end: asNumber(body.end),
    initialCapital: asNumber(body.initial_capital ?? body.initialCapital),
    strategyName:
      body.strategy_name === null || body.strategyName === null
        ? null
        : asString(body.strategy_name ?? body.strategyName, '') || null,
    status: asString(body.status, 'completed'),
    metrics: normalizeMetrics(body.metrics),
    createdAt: asString(body.created_at ?? body.createdAt),
  }
}

export function normalizeTradeDetail(raw: unknown): TradeDetail {
  const t = asRecord(raw)
  return {
    entryTime: asNumber(t.entry_time ?? t.entryTime),
    exitTime: asNumber(t.exit_time ?? t.exitTime),
    entryPrice: asNumber(t.entry_price ?? t.entryPrice),
    exitPrice: asNumber(t.exit_price ?? t.exitPrice),
    side: asString(t.side),
    exitReason: asString(t.exit_reason ?? t.exitReason),
    forcedClose: Boolean(t.forced_close ?? t.forcedClose),
    returnPct: asNumber(t.return_pct ?? t.returnPct),
    size: asNumber(t.size),
    commissionPaid: asNumber(t.commission_paid ?? t.commissionPaid),
    pnlQuote: asNumber(t.pnl_quote ?? t.pnlQuote),
  }
}

export async function listStrategies(): Promise<StrategyInfo[]> {
  const raw = await apiRequest<{ strategies?: unknown }>('/backtest/strategies')
  const list = Array.isArray(raw.strategies) ? raw.strategies : []
  return list.map((item) => {
    const row = asRecord(item)
    const kind = asString(row.kind, 'long_only')
    return {
      name: asString(row.name),
      kind: kind === 'dual' ? 'dual' : 'long_only',
    }
  })
}

export async function runBacktest(input: RunBacktestInput): Promise<BacktestRun> {
  const raw = await apiRequest<unknown>('/backtest', {
    method: 'POST',
    body: JSON.stringify({
      symbol: input.symbol,
      timeframe: input.timeframe,
      start: input.start,
      end: input.end,
      initial_capital: input.initialCapital,
      strategy_name: input.strategyName,
    }),
  })
  return normalizeBacktestRun(raw)
}

export async function getBacktest(runId: string): Promise<BacktestRun> {
  const raw = await apiRequest<unknown>(`/backtest/${encodeURIComponent(runId)}`)
  return normalizeBacktestRun(raw)
}

export async function getBacktestTrades(runId: string): Promise<TradeDetail[]> {
  const raw = await apiRequest<{ trades?: unknown }>(
    `/backtest/${encodeURIComponent(runId)}/trades`,
  )
  const list = Array.isArray(raw.trades) ? raw.trades : []
  return list.map(normalizeTradeDetail)
}

/** Convert YYYY-MM-DD to unix seconds (UTC start or end of day). */
export function dateInputToUnix(date: string, endOfDay: boolean): number {
  const suffix = endOfDay ? 'T23:59:59Z' : 'T00:00:00Z'
  return Math.floor(new Date(`${date}${suffix}`).getTime() / 1000)
}
