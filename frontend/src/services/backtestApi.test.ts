import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  dateInputToUnix,
  normalizeBacktestRun,
  normalizeTradeDetail,
} from '@/services/backtestApi'

describe('backtestApi normalize', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('normalizes snake_case run payloads', () => {
    const run = normalizeBacktestRun({
      run_id: 'abc',
      symbol: 'BTC/USDT',
      timeframe: '1d',
      start: 1,
      end: 2,
      initial_capital: 10000,
      strategy_name: 'demo',
      status: 'completed',
      metrics: {
        total_return: 0.1,
        win_rate: 0.5,
        max_drawdown: 0.2,
        trade_count: 3,
        forced_close: false,
        final_capital: 11000,
        initial_capital: 10000,
      },
      created_at: '2026-01-01T00:00:00Z',
    })
    expect(run.runId).toBe('abc')
    expect(run.metrics.tradeCount).toBe(3)
    expect(run.metrics.totalReturn).toBe(0.1)
  })

  it('normalizes trade detail rows', () => {
    const trade = normalizeTradeDetail({
      entry_time: 10,
      exit_time: 20,
      entry_price: 100,
      exit_price: 110,
      side: 'long',
      exit_reason: 'signal',
      forced_close: false,
      return_pct: 10,
      size: 1000,
      commission_paid: 1,
      pnl_quote: 100,
    })
    expect(trade.entryTime).toBe(10)
    expect(trade.returnPct).toBe(10)
  })

  it('converts date inputs to unix UTC bounds', () => {
    expect(dateInputToUnix('2024-01-01', false)).toBe(1704067200)
    expect(dateInputToUnix('2024-01-01', true)).toBe(1704153599)
  })
})
