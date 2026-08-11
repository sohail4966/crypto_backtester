import { beforeEach, describe, expect, it } from 'vitest'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { createDefaultWorkspace } from '@/services/workspaceStorage'
import { DEFAULT_SYNC_CONFIG } from '@/constants/workspace'

const sampleSymbol = {
  id: 'ETH/USDT',
  ticker: 'ETH/USDT',
  exchange: 'binance',
  baseAsset: 'ETH',
  quoteAsset: 'USDT',
  tickSize: 0.01,
  lotSize: 0.001,
  type: 'spot' as const,
  active: true,
  sortOrder: 2,
}

describe('workspaceStore', () => {
  beforeEach(() => {
    const defaults = createDefaultWorkspace('dark')
    useWorkspaceStore.setState({
      hydrated: true,
      theme: defaults.theme,
      layouts: defaults.layouts,
      activeLayoutId: defaults.activeLayoutId,
      activePaneId: defaults.activePaneId,
      sync: { ...DEFAULT_SYNC_CONFIG },
    })
  })

  it('switches to 2x2 and seeds panes from active', () => {
    useWorkspaceStore.getState().applySymbolToPanes(sampleSymbol, false)
    useWorkspaceStore.getState().setLayoutPreset('2x2')
    const layout = useWorkspaceStore.getState().getActiveLayout()
    expect(layout?.preset).toBe('2x2')
    expect(layout?.panes).toHaveLength(4)
    expect(layout?.panes.every((pane) => pane.symbol?.id === 'ETH/USDT')).toBe(
      true,
    )
  })

  it('updates only active pane when symbol sync off', () => {
    useWorkspaceStore.getState().setLayoutPreset('1x2')
    const panes = useWorkspaceStore.getState().getActiveLayout()!.panes
    useWorkspaceStore.getState().setActivePaneId(panes[0].id)
    useWorkspaceStore.getState().updateActivePaneSymbol(sampleSymbol)
    const next = useWorkspaceStore.getState().getActiveLayout()!.panes
    expect(next[0].symbol?.id).toBe('ETH/USDT')
    expect(next[1].symbol).toBeNull()
  })

  it('fans out symbol when sync.symbol on', () => {
    useWorkspaceStore.getState().setLayoutPreset('1x2')
    useWorkspaceStore.getState().setSyncCategory('symbol', true)
    useWorkspaceStore.getState().updateActivePaneSymbol(sampleSymbol)
    const panes = useWorkspaceStore.getState().getActiveLayout()!.panes
    expect(panes.every((pane) => pane.symbol?.id === 'ETH/USDT')).toBe(true)
  })

  it('persists sync defaults matching D-87', () => {
    const payload = useWorkspaceStore.getState().toPersistPayload()
    expect(payload.sync).toEqual(DEFAULT_SYNC_CONFIG)
  })
})
