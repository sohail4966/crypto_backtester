import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useWorkspaceKeyboard } from '@/hooks/useWorkspaceKeyboard'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { createDefaultWorkspace } from '@/services/workspaceStorage'
import { DEFAULT_SYNC_CONFIG } from '@/constants/workspace'

describe('useWorkspaceKeyboard', () => {
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

  it('Alt+3 selects 2x2', () => {
    const saves: number[] = []
    renderHook(() =>
      useWorkspaceKeyboard({
        onSave: () => {
          saves.push(1)
        },
      }),
    )

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: '3', altKey: true }),
      )
    })
    expect(useWorkspaceStore.getState().getActiveLayout()?.preset).toBe('2x2')
  })

  it('Ctrl+S invokes save', () => {
    const saves: number[] = []
    renderHook(() =>
      useWorkspaceKeyboard({
        onSave: () => {
          saves.push(1)
        },
      }),
    )

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', ctrlKey: true }),
      )
    })
    expect(saves).toHaveLength(1)
  })
})
