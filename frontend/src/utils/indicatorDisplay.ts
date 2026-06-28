import { isMacdKey, type ActiveIndicator, type IndicatorPoint } from '@/types/indicator'
import type { Theme } from '@/types/theme'
import { resolveChartColor } from '@/utils/color'
import { formatPrice } from '@/utils/format'
import { lookupByTime } from '@/utils/timeSeriesLookup'

export const OVERLAY_INDICATOR_COLORS = [
  'var(--color-accent)',
  'var(--color-bull)',
  '#a78bfa',
  '#f59e0b',
  '#38bdf8',
] as const

/** Preset swatches for the indicator settings dialog (theme tokens + fixed hex). */
export const INDICATOR_COLOR_PRESETS = [
  { label: 'Blue', value: 'var(--color-accent)' },
  { label: 'Green', value: 'var(--color-bull)' },
  { label: 'Red', value: 'var(--color-bear)' },
  { label: 'Purple', value: '#a78bfa' },
  { label: 'Amber', value: '#f59e0b' },
  { label: 'Sky', value: '#38bdf8' },
  { label: 'Pink', value: '#f472b6' },
  { label: 'Lime', value: '#84cc16' },
] as const

export const INDICATOR_LINE_WIDTHS = [1, 2, 3, 4] as const

export function defaultIndicatorColor(key: string, paletteIndex: number): string {
  return defaultBundleSeriesColor(key, paletteIndex)
}

/** Default color per series within a multi-line bundle (BB, Keltner, etc.). */
export function defaultBundleSeriesColor(seriesKey: string, lineIndex: number): string {
  const upper = seriesKey.toUpperCase()
  if (upper === 'BB_UPPER' || upper === 'KELTNER_UPPER' || upper === 'DONCHIAN_UPPER') {
    return 'var(--color-accent)'
  }
  if (upper === 'BB_MIDDLE' || upper === 'KELTNER_MIDDLE' || upper === 'DONCHIAN_MIDDLE') {
    return 'var(--color-bull)'
  }
  if (upper === 'BB_LOWER' || upper === 'KELTNER_LOWER' || upper === 'DONCHIAN_LOWER') {
    return '#a78bfa'
  }
  if (upper === 'MACD_LINE') {
    return 'var(--color-accent)'
  }
  if (upper === 'MACD_SIGNAL') {
    return '#f59e0b'
  }
  if (upper === 'MACD_HIST') {
    return 'var(--color-bull)'
  }
  if (upper === 'STOCH_K' || upper === 'STOCHRSI_K') {
    return 'var(--color-accent)'
  }
  if (upper === 'STOCH_D' || upper === 'STOCHRSI_D') {
    return '#f59e0b'
  }
  return OVERLAY_INDICATOR_COLORS[lineIndex % OVERLAY_INDICATOR_COLORS.length]
}

export function bundleSeriesStyleLabel(seriesKey: string): string {
  const upper = seriesKey.toUpperCase()
  const labels: Record<string, string> = {
    BB_UPPER: 'Upper band',
    BB_MIDDLE: 'Middle band',
    BB_LOWER: 'Lower band',
    KELTNER_UPPER: 'Upper band',
    KELTNER_MIDDLE: 'Middle band',
    KELTNER_LOWER: 'Lower band',
    DONCHIAN_UPPER: 'Upper band',
    DONCHIAN_MIDDLE: 'Middle band',
    DONCHIAN_LOWER: 'Lower band',
    MACD_LINE: 'MACD line',
    MACD_SIGNAL: 'Signal',
    MACD_HIST: 'Histogram',
    STOCH_K: '%K',
    STOCH_D: '%D',
    STOCHRSI_K: '%K',
    STOCHRSI_D: '%D',
  }
  return labels[upper] ?? upper.replace(/_/g, ' ')
}

export function colorIndexForInstance(
  active: ActiveIndicator[],
  instanceId: string,
): number {
  const target = active.find((item) => item.instanceId === instanceId)
  if (!target) {
    return 0
  }
  const samePane = active.filter((item) => item.pane === target.pane)
  return Math.max(0, samePane.findIndex((item) => item.instanceId === instanceId))
}

export function resolveIndicatorColor(
  item: Pick<ActiveIndicator, 'key' | 'color'>,
  colorIndex: number,
  theme: Theme,
): string {
  const raw = item.color ?? defaultIndicatorColor(item.key, colorIndex)
  return resolveChartColor(raw, theme)
}

export function indicatorDisplayLabel(
  key: string,
  params: Record<string, unknown>,
): string {
  if (isMacdKey(key)) {
    if (key === 'MACD_HIST') {
      return 'Hist'
    }
    if (key === 'MACD_SIGNAL') {
      return 'Signal'
    }
    return 'MACD'
  }
  const period = params.period
  return period != null ? `${key} ${period}` : key
}

export function indicatorValueAtTime(
  points: IndicatorPoint[],
  time: number,
): number | null {
  return indicatorValueFromLookup(createIndicatorValueLookup(points), time)
}

export function createIndicatorValueLookup(
  points: readonly IndicatorPoint[],
): Map<number, number> {
  const byTime = new Map<number, number>()
  for (const point of points) {
    if (Number.isFinite(point.time) && point.value != null && Number.isFinite(point.value)) {
      byTime.set(point.time, point.value)
    }
  }
  return byTime
}

export function indicatorValueFromLookup(
  lookup: ReadonlyMap<number, number>,
  time: number,
): number | null {
  return lookupByTime(lookup, time)
}

export function formatIndicatorValue(key: string, value: number): string {
  if (key === 'RSI') {
    return value.toFixed(2)
  }
  if (isMacdKey(key)) {
    return value.toFixed(4)
  }
  return formatPrice(value)
}

export function overlayLegendRows(
  items: ActiveIndicator[],
  indicators: Record<string, IndicatorPoint[]>,
  time: number,
  theme: Theme,
): Array<{ label: string; value: string; color: string }> {
  return items.flatMap((item, index) => {
    const value = indicatorValueAtTime(indicators[item.seriesId] ?? [], time)
    if (value == null) {
      return []
    }
    return [
      {
        label: indicatorDisplayLabel(item.key, item.params),
        value: formatIndicatorValue(item.key, value),
        color: resolveIndicatorColor(item, index, theme),
      },
    ]
  })
}
