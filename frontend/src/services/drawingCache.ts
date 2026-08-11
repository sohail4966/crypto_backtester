import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval'
import {
  DRAWINGS_CACHE_KEY,
  DRAWINGS_CACHE_VERSION,
} from '@/constants/drawings'
import type {
  ChartPoint,
  Drawing,
  DrawingsCacheV1,
  DrawingType,
} from '@/types/drawing'

const DRAWING_TYPES: ReadonlySet<DrawingType> = new Set([
  'trend_line',
  'horizontal_line',
  'rectangle',
  'price_range',
  'text_note',
])

function isChartPoint(value: unknown): value is ChartPoint {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  return typeof row.time === 'number' && typeof row.price === 'number'
}

function isHexColor(value: unknown): value is string {
  return typeof value === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(value)
}

export function isValidDrawing(value: unknown): value is Drawing {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (
    typeof row.id !== 'string' ||
    typeof row.type !== 'string' ||
    !DRAWING_TYPES.has(row.type as DrawingType) ||
    typeof row.symbolId !== 'string' ||
    typeof row.timeframe !== 'string' ||
    !isHexColor(row.color) ||
    typeof row.visible !== 'boolean' ||
    typeof row.createdAt !== 'number'
  ) {
    return false
  }

  switch (row.type) {
    case 'trend_line':
      return (
        isChartPoint(row.p1) &&
        isChartPoint(row.p2) &&
        typeof row.lineWidth === 'number'
      )
    case 'horizontal_line':
      return (
        typeof row.price === 'number' &&
        typeof row.lineWidth === 'number' &&
        (row.style === 'solid' || row.style === 'dashed' || row.style === 'dotted')
      )
    case 'rectangle':
      return (
        isChartPoint(row.topLeft) &&
        isChartPoint(row.bottomRight) &&
        typeof row.fillOpacity === 'number'
      )
    case 'price_range':
      return (
        typeof row.entryPrice === 'number' &&
        typeof row.targetPrice === 'number' &&
        typeof row.stopPrice === 'number'
      )
    case 'text_note':
      return (
        typeof row.anchorTime === 'number' &&
        typeof row.anchorPrice === 'number' &&
        typeof row.text === 'string' &&
        row.text.length > 0
      )
    default:
      return false
  }
}

export function isValidDrawingsCache(value: unknown): value is DrawingsCacheV1 {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  if (row.version !== DRAWINGS_CACHE_VERSION) {
    return false
  }
  if (typeof row.savedAt !== 'string') {
    return false
  }
  if (!Array.isArray(row.drawings)) {
    return false
  }
  return row.drawings.every(isValidDrawing)
}

export async function readDrawingsCache(): Promise<DrawingsCacheV1 | null> {
  const raw = await idbGet(DRAWINGS_CACHE_KEY)
  if (raw == null) {
    return null
  }
  if (!isValidDrawingsCache(raw)) {
    await idbDel(DRAWINGS_CACHE_KEY)
    return null
  }
  return raw
}

export async function writeDrawingsCache(drawings: Drawing[]): Promise<void> {
  const cache: DrawingsCacheV1 = {
    version: DRAWINGS_CACHE_VERSION,
    drawings,
    savedAt: new Date().toISOString(),
  }
  if (!isValidDrawingsCache(cache)) {
    throw new Error('Refusing to persist invalid drawings cache')
  }
  await idbSet(DRAWINGS_CACHE_KEY, cache)
}

export async function deleteDrawingsCache(): Promise<void> {
  await idbDel(DRAWINGS_CACHE_KEY)
}
