import { isMacdKey, type ActiveIndicator, type IndicatorPoint } from '@/types/indicator'
import { formatPrice } from '@/utils/format'
import { lookupByTime } from '@/utils/timeSeriesLookup'

export const OVERLAY_INDICATOR_COLORS = [
  'var(--color-accent)',
  'var(--color-bull)',
  '#a78bfa',
  '#f59e0b',
  '#38bdf8',
] as const

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
): Array<{ label: string; value: string; colorIndex: number }> {
  return items.flatMap((item, index) => {
    const value = indicatorValueAtTime(indicators[item.seriesId] ?? [], time)
    if (value == null) {
      return []
    }
    return [
      {
        label: indicatorDisplayLabel(item.key, item.params),
        value: formatIndicatorValue(item.key, value),
        colorIndex: index,
      },
    ]
  })
}
