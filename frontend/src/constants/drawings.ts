import type { DrawingType } from '@/types/drawing'

export const DRAWINGS_CACHE_VERSION = 1 as const

export const DRAWINGS_CACHE_KEY = 'drawings:v1'

export const DRAWING_HIT_THRESHOLD_PX = 6

export const DEFAULT_TREND_LINE_WIDTH = 2
export const DEFAULT_HORIZONTAL_LINE_WIDTH = 1
export const DEFAULT_RECT_FILL_OPACITY = 0.15

export const DRAWING_PERSIST_DEBOUNCE_MS = 150

export interface DrawingToolMeta {
  type: DrawingType
  label: string
  shortcut: string
}

export const DRAWING_TOOLS: readonly DrawingToolMeta[] = [
  { type: 'trend_line', label: 'Trend', shortcut: 'D' },
  { type: 'horizontal_line', label: 'H-Line', shortcut: 'H' },
  { type: 'rectangle', label: 'Rect', shortcut: 'R' },
  { type: 'price_range', label: 'Range', shortcut: 'P' },
  { type: 'text_note', label: 'Text', shortcut: 'T' },
] as const

export const SHORTCUT_TO_TOOL: Record<string, DrawingType> = {
  d: 'trend_line',
  h: 'horizontal_line',
  r: 'rectangle',
  p: 'price_range',
  t: 'text_note',
}
