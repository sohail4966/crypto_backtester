import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useDrawingKeyboard } from '@/hooks/useDrawingKeyboard'
import { useDrawingStore } from '@/stores/drawingStore'
import type { Drawing } from '@/types/drawing'

describe('useDrawingKeyboard', () => {
  beforeEach(() => {
    useDrawingStore.setState({
      drawings: [],
      activeTool: null,
      selectedId: null,
      draft: null,
      hydrated: true,
    })
  })

  it('activates tools via D/H/R/P/T and deletes selection', () => {
    renderHook(() => useDrawingKeyboard())

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }))
    })
    expect(useDrawingStore.getState().activeTool).toBe('trend_line')

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'h' }))
    })
    expect(useDrawingStore.getState().activeTool).toBe('horizontal_line')

    const drawing: Drawing = {
      id: 'del-me',
      type: 'horizontal_line',
      symbolId: 'BTC/USDT',
      timeframe: '1h',
      color: '#58a6ff',
      visible: true,
      createdAt: 1,
      price: 1,
      lineWidth: 1,
      style: 'solid',
    }
    act(() => {
      useDrawingStore.getState().addDrawing(drawing)
    })
    expect(useDrawingStore.getState().selectedId).toBe('del-me')

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete' }))
    })
    expect(useDrawingStore.getState().drawings).toHaveLength(0)
  })

  it('ignores shortcuts while typing in an input', () => {
    renderHook(() => useDrawingKeyboard())
    const input = document.createElement('input')
    document.body.appendChild(input)
    act(() => {
      input.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'd', bubbles: true }),
      )
    })
    expect(useDrawingStore.getState().activeTool).toBeNull()
    input.remove()
  })
})
