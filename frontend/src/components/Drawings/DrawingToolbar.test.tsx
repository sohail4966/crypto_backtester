import { act, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { DrawingToolbar } from '@/components/Drawings/DrawingToolbar'
import { useDrawingStore } from '@/stores/drawingStore'

describe('DrawingToolbar', () => {
  beforeEach(() => {
    useDrawingStore.setState({
      drawings: [],
      activeTool: null,
      selectedId: null,
      draft: null,
      hydrated: true,
    })
  })

  it('exposes five tools and toggles active tool', () => {
    render(<DrawingToolbar />)
    expect(screen.getByRole('toolbar', { name: 'Drawing tools' })).toBeInTheDocument()
    const trend = screen.getByRole('button', { name: /Trend/i })
    act(() => {
      trend.click()
    })
    expect(useDrawingStore.getState().activeTool).toBe('trend_line')
    expect(trend).toHaveAttribute('aria-pressed', 'true')
  })
})
