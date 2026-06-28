export type IndicatorPane = 'overlay' | 'subchart'

export interface IndicatorCatalogEntry {
  key: string
  inputs: string[]
  sharedParams: string[]
  defaultParams: Record<string, unknown>
  pane: IndicatorPane
}

export interface IndicatorSpec {
  key: string
  params: Record<string, unknown>
  pane?: IndicatorPane | null
}

export interface IndicatorPoint {
  time: number
  value: number | null
}

export type IndicatorSeriesMap = Record<string, IndicatorPoint[]>

export interface ActiveIndicator {
  /** Stable client id for UI list keys. */
  instanceId: string
  /** Shared by all series from one add action (e.g. MACD bundle). */
  groupInstanceId: string
  key: string
  params: Record<string, unknown>
  pane: IndicatorPane
  /** Backend map key, e.g. EMA_20 or RSI_14. */
  seriesId: string
  visible: boolean
  /** Hex or theme token (e.g. var(--color-accent)); client-only, not sent to API. */
  color?: string
  /** Line width for overlay/subchart lines (1–4). Client-only. */
  lineWidth?: number
}

/** MACD is three registry keys with shared params — one UI action adds all three. */
export const MACD_KEYS = ['MACD_LINE', 'MACD_SIGNAL', 'MACD_HIST'] as const

export function isMacdKey(key: string): boolean {
  return (MACD_KEYS as readonly string[]).includes(key.toUpperCase())
}
