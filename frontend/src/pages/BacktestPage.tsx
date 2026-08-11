import { useEffect, useState } from 'react'

import {
  dateInputToUnix,
  getBacktestTrades,
  listStrategies,
  runBacktest,
} from '@/services/backtestApi'
import { ApiError } from '@/services/api'
import type { BacktestRun, StrategyInfo, TradeDetail } from '@/types/backtest'

const TIMEFRAMES = ['1h', '4h', '1d', '5m', '15m'] as const

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatTs(unix: number): string {
  return new Date(unix * 1000).toISOString().slice(0, 19).replace('T', ' ')
}

export function BacktestPage() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [symbol, setSymbol] = useState('BTC/USDT')
  const [timeframe, setTimeframe] = useState<string>('1d')
  const [strategyName, setStrategyName] = useState('')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-06-01')
  const [capital, setCapital] = useState('10000')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<BacktestRun | null>(null)
  const [trades, setTrades] = useState<TradeDetail[]>([])

  useEffect(() => {
    let cancelled = false
    void listStrategies()
      .then((items) => {
        if (cancelled) return
        setStrategies(items)
        setStrategyName((current) => current || items[0]?.name || '')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load strategies')
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    setRun(null)
    setTrades([])
    try {
      const result = await runBacktest({
        symbol: symbol.trim(),
        timeframe,
        start: dateInputToUnix(startDate, false),
        end: dateInputToUnix(endDate, true),
        initialCapital: Number(capital) || undefined,
        strategyName,
      })
      setRun(result)
      const detail = await getBacktestTrades(result.runId)
      setTrades(detail)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Backtest failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-text">Backtest</h1>
        <p className="text-sm text-text-secondary">
          Run a named strategy via the Phase 4d HTTP API. Chart overlays on the live
          chart page are deferred — use this page for metrics and trade log.
        </p>
      </header>

      <form
        onSubmit={(event) => {
          void onSubmit(event)
        }}
        className="grid gap-3 rounded border border-border p-4 sm:grid-cols-2"
      >
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Symbol
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Timeframe
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary sm:col-span-2">
          Strategy
          <select
            value={strategyName}
            onChange={(e) => setStrategyName(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
            required
          >
            {strategies.length === 0 ? (
              <option value="">Loading…</option>
            ) : (
              strategies.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name} ({s.kind})
                </option>
              ))
            )}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Start date (UTC)
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          End date (UTC)
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Initial capital
          <input
            type="number"
            min={1}
            step={100}
            value={capital}
            onChange={(e) => setCapital(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none ring-accent focus:ring-1"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading || !strategyName}
            className="rounded bg-accent/20 px-3 py-2 text-sm text-accent disabled:opacity-50"
          >
            {loading ? 'Running…' : 'Run backtest'}
          </button>
        </div>
      </form>

      {error ? (
        <p className="text-sm text-red-500" role="alert">
          {error}
        </p>
      ) : null}

      {run ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
            Results · {run.runId.slice(0, 8)}…
          </h2>
          <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-text-secondary">Trades</dt>
              <dd className="text-text">{run.metrics.tradeCount}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Win rate</dt>
              <dd className="text-text">{pct(run.metrics.winRate)}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Total return</dt>
              <dd className="text-text">{pct(run.metrics.totalReturn)}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Max drawdown</dt>
              <dd className="text-text">{pct(run.metrics.maxDrawdown)}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Final capital</dt>
              <dd className="text-text">{run.metrics.finalCapital.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Sharpe</dt>
              <dd className="text-text">
                {run.metrics.sharpeRatio == null
                  ? '—'
                  : run.metrics.sharpeRatio.toFixed(2)}
              </dd>
            </div>
          </dl>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border text-text-secondary">
                  <th className="px-2 py-1 font-medium">Side</th>
                  <th className="px-2 py-1 font-medium">Entry</th>
                  <th className="px-2 py-1 font-medium">Exit</th>
                  <th className="px-2 py-1 font-medium">Return</th>
                  <th className="px-2 py-1 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-3 text-text-secondary">
                      No trades in this window.
                    </td>
                  </tr>
                ) : (
                  trades.map((trade, index) => (
                    <tr key={`${trade.entryTime}-${index}`} className="border-b border-border/60">
                      <td className="px-2 py-1 text-text">{trade.side}</td>
                      <td className="px-2 py-1 text-text">
                        {formatTs(trade.entryTime)} @ {trade.entryPrice.toFixed(2)}
                      </td>
                      <td className="px-2 py-1 text-text">
                        {formatTs(trade.exitTime)} @ {trade.exitPrice.toFixed(2)}
                      </td>
                      <td className="px-2 py-1 text-text">
                        {trade.returnPct.toFixed(2)}%
                      </td>
                      <td className="px-2 py-1 text-text">{trade.exitReason}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  )
}
