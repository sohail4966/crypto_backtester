import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { LayoutSwitcher } from '@/components/Layout/LayoutSwitcher'
import { SyncConfigPanel } from '@/components/Layout/SyncConfigPanel'
import { createDefaultWorkspace } from '@/services/workspaceStorage'
import { DEFAULT_SYNC_CONFIG } from '@/constants/workspace'
import { useWorkspaceStore } from '@/stores/workspaceStore'

describe('LayoutSwitcher + SyncConfigPanel', () => {
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

  afterEach(() => {
    cleanup()
  })

  it('switches layout preset on click', () => {
    render(<LayoutSwitcher />)
    fireEvent.click(screen.getByRole('button', { name: '2×2' }))
    expect(useWorkspaceStore.getState().getActiveLayout()?.preset).toBe('2x2')
    expect(useWorkspaceStore.getState().getActiveLayout()?.panes).toHaveLength(4)
  })

  it('toggles sync categories', () => {
    render(<SyncConfigPanel />)
    fireEvent.click(screen.getByRole('button', { name: 'Sync' }))
    const crosshair = screen.getByLabelText('Crosshair') as HTMLInputElement
    expect(crosshair.checked).toBe(true)
    fireEvent.click(crosshair)
    expect(useWorkspaceStore.getState().sync.crosshair).toBe(false)

    const symbol = screen.getByLabelText('Symbol') as HTMLInputElement
    expect(symbol.checked).toBe(false)
    fireEvent.click(symbol)
    expect(useWorkspaceStore.getState().sync.symbol).toBe(true)
  })
})
