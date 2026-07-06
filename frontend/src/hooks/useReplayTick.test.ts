import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useReplayTick } from '@/hooks/useReplayTick'
import { useReplayStore } from '@/stores/replayStore'

describe('useReplayTick', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    useReplayStore.setState({
      phase: 'playing',
      serverState: 'playing',
      speed: 10,
      bufferLoading: false,
      tickQueue: [],
      queueRemaining: 0,
      candles: [],
      indicators: {},
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    useReplayStore.getState().resetSession()
  })

  it('requests refill when the local queue is empty even if queueRemaining is zero', () => {
    const sendRefill = vi.fn()

    renderHook(() => useReplayTick({ sendRefill }))

    act(() => {
      vi.advanceTimersByTime(100)
    })

    expect(sendRefill).toHaveBeenCalled()
  })

  it('does not request refill after replay completes', () => {
    const sendRefill = vi.fn()
    useReplayStore.setState({ phase: 'completed', serverState: 'completed' })

    renderHook(() => useReplayTick({ sendRefill }))

    act(() => {
      vi.advanceTimersByTime(1000)
    })

    expect(sendRefill).not.toHaveBeenCalled()
  })
})
