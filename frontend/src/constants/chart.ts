// Windowed loading tunables (SPEC-001 §4.2, D-82). Kept centralized for Phase 6 multi-chart reuse.
export const CHUNK_SIZE_BARS = 500
export const LOOKBACK_CHUNKS = 2
export const LOOKAHEAD_CHUNKS = 1
// Prefetch prior chunk when scroll position is within 20% of the left edge.
export const PREFETCH_THRESHOLD = 0.2

// Default viewport on load and Fit click — TradingView-style density, not the full 500-bar chunk.
export const FIT_VISIBLE_BARS = 120
export const FIT_RIGHT_OFFSET_BARS = 8

export const CHART_SHOW_GRID_STORAGE_KEY = 'chart-show-grid'

export const DEFAULT_TIMEFRAME = '1h'
export const DEFAULT_SYMBOL_ID = 'BTC/USDT'

export const TIMEFRAME_OPTIONS = [
  '1m',
  '5m',
  '15m',
  '30m',
  '1h',
  '4h',
  '1d',
] as const

export type ChartTimeframe = (typeof TIMEFRAME_OPTIONS)[number]
