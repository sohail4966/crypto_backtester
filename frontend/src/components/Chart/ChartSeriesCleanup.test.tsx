import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CandlestickSeries } from '@/components/Chart/CandlestickSeries'
import { ChartContext, type ChartContextValue } from '@/components/Chart/ChartContext'
import { VolumeSeries } from '@/components/Chart/VolumeSeries'

function chartContext(overrides: Partial<ChartContextValue>): ChartContextValue {
  return {
    chart: {
      timeScale: vi.fn(() => ({
        setVisibleLogicalRange: vi.fn(),
      })),
    } as unknown as ChartContextValue['chart'],
    candleSeries: null,
    volumeSeries: null,
    crosshairTime: null,
    registerSubChart: vi.fn(),
    unregisterSubChart: vi.fn(),
    onSubChartCrosshairMove: vi.fn(),
    ...overrides,
  }
}

describe('chart series cleanup', () => {
  it('clears candlestick data when unmounted', () => {
    const setData = vi.fn()
    const { unmount } = render(
      <ChartContext.Provider
        value={chartContext({
          candleSeries: { setData } as unknown as ChartContextValue['candleSeries'],
        })}
      >
        <CandlestickSeries
          fitKey="BTC/USDT-1h"
          candles={[
            {
              time: 1_700_000_000,
              open: 100,
              high: 110,
              low: 90,
              close: 105,
              volume: 12,
            },
          ]}
        />
      </ChartContext.Provider>,
    )

    unmount()

    expect(setData).toHaveBeenLastCalledWith([])
  })

  it('clears volume data when unmounted', () => {
    const setData = vi.fn()
    const applyOptions = vi.fn()
    const { unmount } = render(
      <ChartContext.Provider
        value={chartContext({
          volumeSeries: { applyOptions, setData } as unknown as ChartContextValue['volumeSeries'],
        })}
      >
        <VolumeSeries
          theme="dark"
          candles={[
            {
              time: 1_700_000_000,
              open: 100,
              high: 110,
              low: 90,
              close: 105,
              volume: 12,
            },
          ]}
        />
      </ChartContext.Provider>,
    )

    unmount()

    expect(setData).toHaveBeenLastCalledWith([])
  })
})
