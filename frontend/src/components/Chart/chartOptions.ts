import { ColorType } from 'lightweight-charts'
import { FIT_RIGHT_OFFSET_BARS, MIN_MAIN_PANE_HEIGHT } from '@/constants/chart'
import type { ChartTimezoneId } from '@/constants/timezone'
import type { Theme } from '@/types/theme'
import {
  createChartTimezoneFormatters,
  resolveChartTimeZone,
} from '@/utils/chartTimezone'
import { resolveChartColor } from '@/utils/color'

const MIN_CHART_HEIGHT = MIN_MAIN_PANE_HEIGHT

export function chartOptions(theme: Theme, showGrid: boolean, timezone: ChartTimezoneId) {
  const { timeFormatter, tickMarkFormatter } = createChartTimezoneFormatters(
    resolveChartTimeZone(timezone),
  )
  const gridColor = resolveChartColor('var(--color-border)', theme)
  return {
    autoSize: false,
    layout: {
      background: { type: ColorType.Solid, color: resolveChartColor('var(--color-bg)', theme) },
      textColor: resolveChartColor('var(--color-text-secondary)', theme),
      attributionLogo: false,
    },
    grid: {
      vertLines: { visible: showGrid, color: gridColor },
      horzLines: { visible: showGrid, color: gridColor },
    },
    rightPriceScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
    },
    localization: {
      timeFormatter,
    },
    timeScale: {
      borderColor: resolveChartColor('var(--color-border)', theme),
      timeVisible: true,
      secondsVisible: false,
      rightOffset: FIT_RIGHT_OFFSET_BARS,
      tickMarkFormatter,
    },
    crosshair: {
      vertLine: { color: resolveChartColor('var(--color-accent)', theme) },
      horzLine: { color: resolveChartColor('var(--color-accent)', theme) },
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: true,
    },
    handleScale: {
      mouseWheel: true,
      pinch: true,
      axisPressedMouseMove: { time: true, price: true },
      axisDoubleClickReset: { time: true, price: true },
    },
  } as const
}

export function subPaneGridOptions(theme: Theme, showGrid: boolean) {
  const gridColor = resolveChartColor('var(--color-border)', theme)
  return {
    vertLines: { visible: false },
    horzLines: { visible: showGrid, color: gridColor },
  }
}

export function seriesColors(theme: Theme) {
  return {
    upColor: resolveChartColor('var(--color-bull)', theme),
    downColor: resolveChartColor('var(--color-bear)', theme),
    borderUpColor: resolveChartColor('var(--color-bull)', theme),
    borderDownColor: resolveChartColor('var(--color-bear)', theme),
    wickUpColor: resolveChartColor('var(--color-bull)', theme),
    wickDownColor: resolveChartColor('var(--color-bear)', theme),
  }
}

export function measureChartArea(container: HTMLDivElement, height?: number) {
  const { width, height: rectHeight } = container.getBoundingClientRect()
  const resolvedHeight = height ?? rectHeight
  return {
    width: Math.max(1, Math.floor(width)),
    height: Math.max(MIN_CHART_HEIGHT, Math.floor(resolvedHeight)),
  }
}
