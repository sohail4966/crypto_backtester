import { create } from 'zustand'
import type { BacktestSignal, TradeDetail } from '@/types/backtest'

interface BacktestOverlayState {
  runId: string | null
  symbol: string | null
  timeframe: string | null
  signals: BacktestSignal[]
  trades: TradeDetail[]
  setFromRun: (input: {
    runId: string
    symbol: string
    timeframe: string
    signals: BacktestSignal[]
    trades: TradeDetail[]
  }) => void
  clear: () => void
}

export const useBacktestOverlayStore = create<BacktestOverlayState>((set) => ({
  runId: null,
  symbol: null,
  timeframe: null,
  signals: [],
  trades: [],
  setFromRun: (input) =>
    set({
      runId: input.runId,
      symbol: input.symbol,
      timeframe: input.timeframe,
      signals: input.signals,
      trades: input.trades,
    }),
  clear: () =>
    set({
      runId: null,
      symbol: null,
      timeframe: null,
      signals: [],
      trades: [],
    }),
}))
