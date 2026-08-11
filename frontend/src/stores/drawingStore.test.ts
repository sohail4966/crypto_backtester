import { beforeEach, describe, expect, it } from 'vitest'
import {
  createDrawingId,
  drawingsFor,
  useDrawingStore,
} from '@/stores/drawingStore'
import type { Drawing } from '@/types/drawing'

function baseTrend(overrides: Partial<Drawing> = {}): Drawing {
  return {
    id: createDrawingId(),
    type: 'trend_line',
    symbolId: 'BTC/USDT',
    timeframe: '1h',
    color: '#58a6ff',
    visible: true,
    createdAt: 1,
    p1: { time: 1, price: 100 },
    p2: { time: 2, price: 110 },
    lineWidth: 2,
    ...overrides,
  } as Drawing
}

describe('drawingStore', () => {
  beforeEach(() => {
    useDrawingStore.setState({
      drawings: [],
      activeTool: null,
      selectedId: null,
      draft: null,
      hydrated: false,
    })
  })

  it('hydrates drawings and clears interaction state', () => {
    const drawing = baseTrend()
    useDrawingStore.getState().setActiveTool('trend_line')
    useDrawingStore.getState().hydrate([drawing])
    const state = useDrawingStore.getState()
    expect(state.drawings).toEqual([drawing])
    expect(state.hydrated).toBe(true)
    expect(state.activeTool).toBeNull()
    expect(state.draft).toBeNull()
  })

  it('adds a drawing with hex color and clears the tool', () => {
    useDrawingStore.getState().setActiveTool('horizontal_line')
    const drawing: Drawing = {
      id: 'h1',
      type: 'horizontal_line',
      symbolId: 'BTC/USDT',
      timeframe: '1h',
      color: '#58a6ff',
      visible: true,
      createdAt: 1,
      price: 42,
      lineWidth: 1,
      style: 'solid',
    }
    useDrawingStore.getState().addDrawing(drawing)
    const state = useDrawingStore.getState()
    expect(state.drawings).toHaveLength(1)
    expect(state.drawings[0]?.color).toBe('#58a6ff')
    expect(state.activeTool).toBeNull()
    expect(state.selectedId).toBe('h1')
  })

  it('filters by symbol and timeframe', () => {
    const a = baseTrend({ id: 'a', symbolId: 'BTC/USDT', timeframe: '1h' })
    const b = baseTrend({ id: 'b', symbolId: 'ETH/USDT', timeframe: '1h' })
    const c = baseTrend({ id: 'c', symbolId: 'BTC/USDT', timeframe: '1m' })
    useDrawingStore.getState().hydrate([a, b, c])
    expect(drawingsFor(useDrawingStore.getState().drawings, 'BTC/USDT', '1h')).toEqual([
      a,
    ])
  })

  it('Esc clears draft then tool then selection', () => {
    const store = useDrawingStore.getState()
    store.setActiveTool('trend_line')
    store.setDraft({ type: 'trend_line', p1: { time: 1, price: 1 } })
    expect(store.handleEscape()).toBe(true)
    expect(useDrawingStore.getState().draft).toBeNull()
    expect(useDrawingStore.getState().activeTool).toBe('trend_line')

    expect(useDrawingStore.getState().handleEscape()).toBe(true)
    expect(useDrawingStore.getState().activeTool).toBeNull()

    useDrawingStore.getState().addDrawing(baseTrend({ id: 'sel' }))
    expect(useDrawingStore.getState().selectedId).toBe('sel')
    expect(useDrawingStore.getState().handleEscape()).toBe(true)
    expect(useDrawingStore.getState().selectedId).toBeNull()
    expect(useDrawingStore.getState().handleEscape()).toBe(false)
  })

  it('removes the selected drawing', () => {
    useDrawingStore.getState().addDrawing(baseTrend({ id: 'x' }))
    useDrawingStore.getState().removeSelected()
    expect(useDrawingStore.getState().drawings).toHaveLength(0)
    expect(useDrawingStore.getState().selectedId).toBeNull()
  })
})
