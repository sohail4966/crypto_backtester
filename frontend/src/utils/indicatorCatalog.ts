import {
  MACD_KEYS,
  type ActiveIndicator,
  type IndicatorCatalogEntry,
  type IndicatorPane,
  isMacdKey,
} from '@/types/indicator'
import { indicatorSeriesId } from '@/utils/indicatorId'

/** Primary picker keys that expand to multiple registry series. */
export const BUNDLE_EXPANSIONS: Record<string, readonly string[]> = {
  MACD_LINE: MACD_KEYS,
  BB_UPPER: ['BB_UPPER', 'BB_MIDDLE', 'BB_LOWER'],
  STOCH_K: ['STOCH_K', 'STOCH_D'],
  STOCHRSI_K: ['STOCHRSI_K', 'STOCHRSI_D'],
  KELTNER_UPPER: ['KELTNER_UPPER', 'KELTNER_MIDDLE', 'KELTNER_LOWER'],
  DONCHIAN_UPPER: ['DONCHIAN_UPPER', 'DONCHIAN_MIDDLE', 'DONCHIAN_LOWER'],
  ICHIMOKU_TENKAN: [
    'ICHIMOKU_TENKAN',
    'ICHIMOKU_KIJUN',
    'ICHIMOKU_SENKOU_A',
    'ICHIMOKU_SENKOU_B',
    'ICHIMOKU_CHIKOU',
  ],
  PIVOT_P: [
    'PIVOT_P',
    'PIVOT_R1',
    'PIVOT_R2',
    'PIVOT_R3',
    'PIVOT_S1',
    'PIVOT_S2',
    'PIVOT_S3',
  ],
}

export function bundleKeysFor(key: string): readonly string[] {
  return BUNDLE_EXPANSIONS[key.toUpperCase()] ?? [key.toUpperCase()]
}

export function primaryBundleKey(key: string): string | null {
  const upper = key.toUpperCase()
  for (const [primary, keys] of Object.entries(BUNDLE_EXPANSIONS)) {
    if ((keys as readonly string[]).includes(upper)) {
      return primary
    }
  }
  return null
}

export function bundleGroupKey(key: string, params: Record<string, unknown>): string {
  const primary = primaryBundleKey(key)
  if (primary) {
    return `${primary}:${JSON.stringify(params)}`
  }
  return indicatorSeriesId(key, params)
}

/** Registry keys hidden from the add picker (siblings of a bundle). */
export const PICKER_SKIP_KEYS = new Set([
  'MACD_SIGNAL',
  'MACD_HIST',
  'BB_MIDDLE',
  'BB_LOWER',
  'STOCH_D',
  'STOCHRSI_D',
  'KELTNER_MIDDLE',
  'KELTNER_LOWER',
  'DONCHIAN_MIDDLE',
  'DONCHIAN_LOWER',
  'ICHIMOKU_KIJUN',
  'ICHIMOKU_SENKOU_A',
  'ICHIMOKU_SENKOU_B',
  'ICHIMOKU_CHIKOU',
  'PIVOT_R1',
  'PIVOT_R2',
  'PIVOT_R3',
  'PIVOT_S1',
  'PIVOT_S2',
  'PIVOT_S3',
])

export type ParamFieldType = 'integer' | 'float' | 'select'

export interface ParamFieldDef {
  name: string
  label: string
  type: ParamFieldType
  options?: string[]
  min?: number
  step?: number
}

const PARAM_LABELS: Record<string, string> = {
  period: 'Length',
  fast: 'Fast length',
  slow: 'Slow length',
  signal: 'Signal smoothing',
  std: 'Std dev',
  fastk_period: 'Fast %K',
  slowk_period: 'Slow %K',
  slowd_period: '%D',
  fastd_period: 'Fast %D',
  acceleration: 'Acceleration',
  maximum: 'Maximum',
  nbdev: 'Std dev multiplier',
  multiplier: 'Multiplier',
  variant: 'Variant',
  tenkan: 'Conversion line',
  kijun: 'Base line',
  senkou_b: 'Leading span B',
  displacement: 'Displacement',
  annualization: 'Annualization',
  atr_period: 'ATR length',
  short_period: 'Short length',
  long_period: 'Long length',
  fast_period: 'Fast length',
  slow_period: 'Slow length',
}

export function normalizeCatalogEntry(row: Record<string, unknown>): IndicatorCatalogEntry {
  return {
    key: String(row.key),
    inputs: (row.inputs as string[]) ?? [],
    sharedParams: (row.shared_params as string[]) ?? (row.sharedParams as string[]) ?? [],
    defaultParams:
      (row.default_params as Record<string, unknown>) ??
      (row.defaultParams as Record<string, unknown>) ??
      {},
    pane: (row.pane as IndicatorPane) ?? 'overlay',
  }
}

export function catalogPickerLabel(entry: IndicatorCatalogEntry): string {
  if (isMacdKey(entry.key)) {
    return 'MACD'
  }
  if (entry.key.startsWith('BB_')) {
    return 'Bollinger Bands'
  }
  if (entry.key.startsWith('STOCH_') && entry.key !== 'STOCHRSI_K') {
    return 'Stochastic'
  }
  if (entry.key.startsWith('STOCHRSI_')) {
    return 'Stoch RSI'
  }
  if (entry.key.startsWith('KELTNER_')) {
    return 'Keltner Channels'
  }
  if (entry.key.startsWith('DONCHIAN_')) {
    return 'Donchian Channels'
  }
  if (entry.key.startsWith('ICHIMOKU_')) {
    return 'Ichimoku'
  }
  if (entry.key.startsWith('PIVOT_')) {
    return 'Pivot Points'
  }
  const period = entry.defaultParams.period
  return period != null ? `${entry.key} (${period})` : entry.key
}

export function pickerCatalogEntries(
  rows: IndicatorCatalogEntry[],
): IndicatorCatalogEntry[] {
  return rows
    .filter((entry) => !PICKER_SKIP_KEYS.has(entry.key))
    .sort((a, b) => catalogPickerLabel(a).localeCompare(catalogPickerLabel(b)))
}

export function findCatalogEntry(
  catalog: IndicatorCatalogEntry[],
  key: string,
): IndicatorCatalogEntry | undefined {
  const upper = key.toUpperCase()
  return catalog.find((entry) => entry.key === upper)
}

export function paramFieldDefs(entry: IndicatorCatalogEntry): ParamFieldDef[] {
  const names =
    entry.sharedParams.length > 0
      ? entry.sharedParams
      : Object.keys(entry.defaultParams)

  return names.map((name) => {
    if (name === 'variant') {
      return {
        name,
        label: PARAM_LABELS[name] ?? name,
        type: 'select',
        options: ['rolling', 'session'],
      }
    }

    const sample = entry.defaultParams[name]
    const isFloat =
      typeof sample === 'number' && !Number.isInteger(sample) ||
      name === 'std' ||
      name === 'multiplier' ||
      name === 'acceleration' ||
      name === 'maximum' ||
      name === 'nbdev'

    return {
      name,
      label: PARAM_LABELS[name] ?? name.replace(/_/g, ' '),
      type: isFloat ? 'float' : 'integer',
      min: isFloat ? 0.0001 : 1,
      step: isFloat ? 0.01 : 1,
    }
  })
}

export function indicatorChipLabel(key: string, params: Record<string, unknown>): string {
  if (isMacdKey(key)) {
    const fast = params.fast
    const slow = params.slow
    const signal = params.signal
    if (fast != null && slow != null && signal != null) {
      return `MACD ${fast} ${slow} ${signal}`
    }
    return 'MACD'
  }
  if (key.startsWith('BB_')) {
    const period = params.period
    const std = params.std
    return period != null && std != null ? `BB ${period} ${std}` : 'Bollinger Bands'
  }
  const period = params.period
  return period != null ? `${key} ${period}` : key
}

export function indicatorTabEntries(
  active: ActiveIndicator[],
  pane?: IndicatorPane,
): Array<{
  instanceId: string
  label: string
  visible: boolean
  hasSettings: boolean
}> {
  const seen = new Set<string>()
  const list: Array<{
    instanceId: string
    label: string
    visible: boolean
    hasSettings: boolean
  }> = []

  for (const item of active) {
    if (pane != null && item.pane !== pane) {
      continue
    }
    const groupKey = bundleGroupKey(item.key, item.params)
    if (seen.has(groupKey)) {
      continue
    }
    seen.add(groupKey)
    list.push({
      instanceId: item.instanceId,
      label: indicatorChipLabel(item.key, item.params),
      visible: item.visible !== false,
      hasSettings: Object.keys(item.params).length > 0,
    })
  }

  return list
}
