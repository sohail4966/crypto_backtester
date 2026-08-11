import { useEffect } from 'react'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useTheme } from '@/hooks/useTheme'
import { useBacktestOverlayStore } from '@/stores/backtestOverlayStore'
import { buildBacktestMarkers } from '@/utils/backtestMarkers'

interface BacktestMarkersProps {
  /** Only draw when the chart symbol/timeframe matches the selected run. */
  symbolId: string | undefined
  timeframe: string
}

/** Applies backtest signal/trade markers onto the main candle series when a run is selected. */
export function BacktestMarkers({ symbolId, timeframe }: BacktestMarkersProps) {
  const { candleSeries } = useChartContext()
  const { theme } = useTheme()
  const runId = useBacktestOverlayStore((s) => s.runId)
  const overlaySymbol = useBacktestOverlayStore((s) => s.symbol)
  const overlayTimeframe = useBacktestOverlayStore((s) => s.timeframe)
  const signals = useBacktestOverlayStore((s) => s.signals)
  const trades = useBacktestOverlayStore((s) => s.trades)

  useEffect(() => {
    if (!candleSeries || typeof candleSeries.setMarkers !== 'function') {
      return
    }

    const matches =
      runId != null &&
      overlaySymbol != null &&
      symbolId === overlaySymbol &&
      timeframe === overlayTimeframe

    if (!matches) {
      candleSeries.setMarkers([])
      return
    }

    candleSeries.setMarkers(buildBacktestMarkers(signals, trades, theme))
    return () => {
      candleSeries.setMarkers([])
    }
  }, [
    candleSeries,
    overlaySymbol,
    overlayTimeframe,
    runId,
    signals,
    symbolId,
    theme,
    timeframe,
    trades,
  ])

  return null
}
