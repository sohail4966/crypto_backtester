import { render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChartContext, type ChartContextValue } from '@/components/Chart/ChartContext'
import { IndicatorSubPane } from '@/components/Indicators/IndicatorSubPane'
import type { ActiveIndicator, IndicatorSeriesMap } from '@/types/indicator'

const firstLineSeries = {
  applyOptions: vi.fn(),
  setData: vi.fn(),
}
const secondLineSeries = {
  applyOptions: vi.fn(),
  setData: vi.fn(),
}

const subChart = {
  addHistogramSeries: vi.fn(),
  addLineSeries: vi.fn(),
  applyOptions: vi.fn(),
  remove: vi.fn(),
  removeSeries: vi.fn(),
  subscribeCrosshairMove: vi.fn(),
  timeScale: vi.fn(() => ({
    getVisibleLogicalRange: vi.fn(() => null),
    setVisibleLogicalRange: vi.fn(),
  })),
  unsubscribeCrosshairMove: vi.fn(),
}

vi.mock('lightweight-charts', () => ({
  ColorType: { Solid: 'Solid' },
  createChart: vi.fn(() => subChart),
}))

vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}))

const showGridState = { value: true }

vi.mock('@/stores/chartStore', () => ({
  useChartStore: (selector: (state: { showGrid: boolean }) => unknown) =>
    selector({ showGrid: showGridState.value }),
}))

function indicator(seriesId: string, key = seriesId): ActiveIndicator {
  return {
    instanceId: seriesId,
    key,
    params: { period: 14 },
    pane: 'subchart',
    seriesId,
    visible: true,
  }
}

const indicators: IndicatorSeriesMap = {
  RSI_14: [
    { time: 100, value: 40 },
    { time: 200, value: 50 },
  ],
  RSI_MA_14: [
    { time: 100, value: 42 },
    { time: 200, value: 48 },
  ],
}

function mainChartContext(): ChartContextValue {
  return {
    chart: {
      timeScale: vi.fn(() => ({
        getVisibleLogicalRange: vi.fn(() => ({ from: 0, to: 10 })),
        subscribeVisibleLogicalRangeChange: vi.fn(),
        unsubscribeVisibleLogicalRangeChange: vi.fn(),
      })),
    } as unknown as ChartContextValue['chart'],
    candleSeries: null,
    volumeSeries: null,
    crosshairTime: null,
    registerSubChart: vi.fn(),
    unregisterSubChart: vi.fn(),
    onSubChartCrosshairMove: vi.fn(),
  }
}

function WithContext({ children }: { children: ReactNode }) {
  return <ChartContext.Provider value={mainChartContext()}>{children}</ChartContext.Provider>
}

describe('IndicatorSubPane', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    showGridState.value = true
    subChart.addLineSeries
      .mockReturnValueOnce(firstLineSeries)
      .mockReturnValueOnce(secondLineSeries)
  })

  it('removes chart series that are no longer in the active group', async () => {
    const { rerender } = render(
      <WithContext>
        <IndicatorSubPane
          paneId="rsi-pane"
          group={[indicator('RSI_14', 'RSI'), indicator('RSI_MA_14', 'RSI_MA')]}
          indicators={indicators}
          chartHeight={112}
        />
      </WithContext>,
    )

    await waitFor(() => expect(subChart.addLineSeries).toHaveBeenCalledTimes(2))

    rerender(
      <WithContext>
        <IndicatorSubPane
          paneId="rsi-pane"
          group={[indicator('RSI_14', 'RSI')]}
          indicators={indicators}
          chartHeight={112}
        />
      </WithContext>,
    )

    await waitFor(() => expect(subChart.removeSeries).toHaveBeenCalledWith(secondLineSeries))
    expect(subChart.removeSeries).not.toHaveBeenCalledWith(firstLineSeries)
  })

  it('hides horizontal grid lines when showGrid is false', async () => {
    showGridState.value = false

    render(
      <WithContext>
        <IndicatorSubPane
          paneId="rsi-pane"
          group={[indicator('RSI_14', 'RSI')]}
          indicators={indicators}
          chartHeight={112}
        />
      </WithContext>,
    )

    await waitFor(() => expect(subChart.applyOptions).toHaveBeenCalled())
    expect(subChart.applyOptions).toHaveBeenCalledWith(
      expect.objectContaining({
        grid: {
          vertLines: { visible: false },
          horzLines: { visible: false, color: expect.any(String) },
        },
      }),
    )
  })
})
