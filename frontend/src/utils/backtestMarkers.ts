import type { SeriesMarker, UTCTimestamp } from 'lightweight-charts'
import type { Theme } from '@/types/theme'
import type { BacktestSignal, TradeDetail } from '@/types/backtest'
import { resolveChartColor } from '@/utils/color'
import { toUtcTimestamp } from '@/utils/chartSeriesData'

function isLongSide(side: string): boolean {
  const normalized = side.trim().toLowerCase()
  return (
    normalized === 'buy' ||
    normalized === 'long' ||
    normalized === 'entry_long' ||
    normalized.startsWith('long')
  )
}

function isShortSide(side: string): boolean {
  const normalized = side.trim().toLowerCase()
  return (
    normalized === 'sell' ||
    normalized === 'short' ||
    normalized === 'entry_short' ||
    normalized.startsWith('short')
  )
}

/** Map backtest signals/trades to lightweight-charts series markers (FE-007 / G-013). */
export function buildBacktestMarkers(
  signals: BacktestSignal[],
  trades: TradeDetail[],
  theme: Theme,
): SeriesMarker<UTCTimestamp>[] {
  const bull = resolveChartColor('var(--color-bull)', theme)
  const bear = resolveChartColor('var(--color-bear)', theme)
  const muted = resolveChartColor('var(--color-text-secondary)', theme)
  const markers: SeriesMarker<UTCTimestamp>[] = []

  for (const signal of signals) {
    const time = toUtcTimestamp(signal.time)
    if (time == null) continue
    const long = isLongSide(signal.side)
    const short = isShortSide(signal.side)
    markers.push({
      time,
      position: long ? 'belowBar' : 'aboveBar',
      shape: long ? 'arrowUp' : short ? 'arrowDown' : 'circle',
      color: long ? bull : short ? bear : muted,
      text: signal.side.slice(0, 1).toUpperCase(),
    })
  }

  for (const trade of trades) {
    const entry = toUtcTimestamp(trade.entryTime)
    if (entry != null) {
      const long = isLongSide(trade.side)
      markers.push({
        time: entry,
        position: long ? 'belowBar' : 'aboveBar',
        shape: long ? 'arrowUp' : 'arrowDown',
        color: long ? bull : bear,
        text: 'E',
      })
    }
    const exit = toUtcTimestamp(trade.exitTime)
    if (exit != null) {
      markers.push({
        time: exit,
        position: 'inBar',
        shape: 'circle',
        color: muted,
        text: 'X',
      })
    }
  }

  return markers.sort((a, b) => Number(a.time) - Number(b.time))
}
