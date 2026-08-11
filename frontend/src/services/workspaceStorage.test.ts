import { beforeEach, describe, expect, it } from 'vitest'
import {
  createDefaultWorkspace,
  isValidWorkspaceCache,
  normalizeWorkspaceIds,
  readWorkspaceCache,
  resizePanesForPreset,
  writeWorkspaceCache,
  deleteWorkspaceCache,
} from '@/services/workspaceStorage'
import { WORKSPACE_CACHE_KEY } from '@/constants/workspace'
import { get as idbGet, set as idbSet } from 'idb-keyval'

const sampleSymbol = {
  id: 'BTC/USDT',
  ticker: 'BTC/USDT',
  exchange: 'binance',
  baseAsset: 'BTC',
  quoteAsset: 'USDT',
  tickSize: 0.01,
  lotSize: 0.001,
  type: 'spot' as const,
  active: true,
  sortOrder: 1,
}

describe('workspaceStorage', () => {
  beforeEach(async () => {
    await deleteWorkspaceCache()
  })

  it('round-trips a valid workspace blob', async () => {
    const base = createDefaultWorkspace('dark')
    base.layouts[0].panes[0].symbol = sampleSymbol
    await writeWorkspaceCache(base)
    const read = await readWorkspaceCache()
    expect(read).not.toBeNull()
    expect(read?.theme).toBe('dark')
    expect(read?.layouts[0].panes[0].symbol?.id).toBe('BTC/USDT')
    expect(read?.sync.crosshair).toBe(true)
    expect(read?.sync.symbol).toBe(false)
  })

  it('discards corrupt blobs', async () => {
    await idbSet(WORKSPACE_CACHE_KEY, { version: 1, garbage: true })
    expect(await readWorkspaceCache()).toBeNull()
    expect(await idbGet(WORKSPACE_CACHE_KEY)).toBeUndefined()
  })

  it('normalizeWorkspaceIds falls back when active ids missing', () => {
    const base = createDefaultWorkspace()
    const normalized = normalizeWorkspaceIds({
      ...base,
      activeLayoutId: 'missing',
      activePaneId: 'missing',
    })
    expect(normalized.activeLayoutId).toBe(base.layouts[0].id)
    expect(normalized.activePaneId).toBe(base.layouts[0].panes[0].id)
  })

  it('resizePanesForPreset expands and shrinks', () => {
    const base = createDefaultWorkspace()
    base.layouts[0].panes[0].symbol = sampleSymbol
    const four = resizePanesForPreset(base.layouts[0].panes, '2x2')
    expect(four).toHaveLength(4)
    expect(four[1].symbol?.id).toBe('BTC/USDT')
    const one = resizePanesForPreset(four, '1x1')
    expect(one).toHaveLength(1)
  })

  it('rejects invalid theme', () => {
    const base = createDefaultWorkspace()
    expect(
      isValidWorkspaceCache({ ...base, theme: 'neon' }),
    ).toBe(false)
  })
})
