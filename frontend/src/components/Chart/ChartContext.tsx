/** Shares one lw-charts instance per pane — series components stay stateless (SPEC-001 §3). */
import { createContext, useContext } from 'react'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'

export interface ChartContextValue {
  chart: IChartApi | null
  candleSeries: ISeriesApi<'Candlestick'> | null
  volumeSeries: ISeriesApi<'Histogram'> | null
}

export const ChartContext = createContext<ChartContextValue>({
  chart: null,
  candleSeries: null,
  volumeSeries: null,
})

export function useChartContext(): ChartContextValue {
  return useContext(ChartContext)
}
