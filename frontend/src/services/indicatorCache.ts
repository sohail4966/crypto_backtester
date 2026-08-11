import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval'
import type { ActiveIndicator } from '@/types/indicator'

export const INDICATOR_CACHE_KEY = 'indicators:v1'
export const INDICATOR_CACHE_VERSION = 1 as const

export type IndicatorCacheV1 = {
  version: typeof INDICATOR_CACHE_VERSION
  /** Schema bump path for FE-014 pane-keyed migration. */
  schema: 'global' | 'byPane'
  savedAt: string
  /** Legacy global list (schema === 'global'). */
  active?: ActiveIndicator[]
  /** Per-pane active sets (schema === 'byPane'). */
  byPane?: Record<string, ActiveIndicator[]>
}

function isActiveIndicator(value: unknown): value is ActiveIndicator {
  if (!value || typeof value !== 'object') {
    return false
  }
  const row = value as Record<string, unknown>
  return (
    typeof row.instanceId === 'string' &&
    typeof row.groupInstanceId === 'string' &&
    typeof row.key === 'string' &&
    typeof row.seriesId === 'string' &&
    (row.pane === 'overlay' || row.pane === 'subchart') &&
    row.params != null &&
    typeof row.params === 'object'
  )
}

export async function readIndicatorCache(): Promise<IndicatorCacheV1 | null> {
  const raw = await idbGet(INDICATOR_CACHE_KEY)
  if (!raw || typeof raw !== 'object') {
    return null
  }
  const row = raw as Record<string, unknown>
  if (row.version !== INDICATOR_CACHE_VERSION) {
    return null
  }
  if (row.schema === 'byPane' && row.byPane && typeof row.byPane === 'object') {
    const byPane: Record<string, ActiveIndicator[]> = {}
    for (const [paneId, list] of Object.entries(
      row.byPane as Record<string, unknown>,
    )) {
      if (!Array.isArray(list)) {
        continue
      }
      byPane[paneId] = list.filter(isActiveIndicator)
    }
    return {
      version: INDICATOR_CACHE_VERSION,
      schema: 'byPane',
      savedAt: typeof row.savedAt === 'string' ? row.savedAt : new Date().toISOString(),
      byPane,
    }
  }
  if (Array.isArray(row.active)) {
    return {
      version: INDICATOR_CACHE_VERSION,
      schema: 'global',
      savedAt: typeof row.savedAt === 'string' ? row.savedAt : new Date().toISOString(),
      active: row.active.filter(isActiveIndicator),
    }
  }
  return null
}

export async function writeIndicatorCache(cache: IndicatorCacheV1): Promise<void> {
  await idbSet(INDICATOR_CACHE_KEY, cache)
}

export async function deleteIndicatorCache(): Promise<void> {
  await idbDel(INDICATOR_CACHE_KEY)
}
