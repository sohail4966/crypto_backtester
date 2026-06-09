import { create } from 'zustand'
import {
  DEFAULT_SYMBOL_ID,
  DEFAULT_TIMEFRAME,
  type ChartTimeframe,
} from '@/constants/chart'
import type { Symbol } from '@/types/symbol'

interface ChartState {
  // Structured Symbol entity (D-86) — API calls use symbol.id, never raw ticker strings.
  symbol: Symbol | null
  timeframe: ChartTimeframe
  setSymbol: (symbol: Symbol) => void
  setTimeframe: (timeframe: ChartTimeframe) => void
}

export const useChartStore = create<ChartState>((set) => ({
  symbol: null,
  timeframe: DEFAULT_TIMEFRAME,
  setSymbol: (symbol) => set({ symbol }),
  setTimeframe: (timeframe) => set({ timeframe }),
}))

export const defaultSymbolId = DEFAULT_SYMBOL_ID
