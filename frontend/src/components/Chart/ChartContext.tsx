/** Shares one lw-charts instance per pane — series components stay stateless (SPEC-001 §3). */
import { createContext, useContext } from 'react'
import type { IChartApi, ISeriesApi, MouseEventParams, SeriesType } from 'lightweight-charts'

export interface SubChartHandle {
  chart: IChartApi
  getPrimarySeries: () => ISeriesApi<SeriesType> | null
  getPriceAtTime: (time: number) => number | null
}

export interface ChartContextValue {
  chart: IChartApi | null
  candleSeries: ISeriesApi<'Candlestick'> | null
  volumeSeries: ISeriesApi<'Histogram'> | null
  crosshairTime: number | null
  registerSubChart: (id: string, handle: SubChartHandle) => void
  unregisterSubChart: (id: string) => void
  onSubChartCrosshairMove: (param: MouseEventParams) => void
}

const noop = () => {}

export const ChartContext = createContext<ChartContextValue>({
  chart: null,
  candleSeries: null,
  volumeSeries: null,
  crosshairTime: null,
  registerSubChart: noop,
  unregisterSubChart: noop,
  onSubChartCrosshairMove: noop,
})

export function useChartContext(): ChartContextValue {
  return useContext(ChartContext)
}
