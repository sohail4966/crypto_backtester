import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useReplayTick } from '@/hooks/useReplayTick'
import { useReplayStore } from '@/stores/replayStore'
import type { ReplayTick } from '@/types/replay'

const tick = (time: number): ReplayTick => ({
  bar: { time, open: 1, high: 2, low: 0.5, close: 1.5, volume: 1 },
  indicators: {},
})

describe('useReplayTick', () => {
  beforeEach(() => {
    useReplayStore.getState().reset()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('advances one bar per interval and sends refill below threshold', () => {
    const send = vi.fn()
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks(Array.from({ length: 5 }, (_, i) => tick(100 + i)))
    store.setPhase('playing')

    renderHook(() =>
      useReplayTick({
        getWsClient: () => ({ send }) as never,
      }),
    )

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(useReplayStore.getState().trailBars).toHaveLength(1)
    expect(send).toHaveBeenCalledWith({ action: 'refill' })
  })

  it('stops draining when paused', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks([tick(100), tick(200)])
    store.setPhase('playing')

    const { rerender } = renderHook(() =>
      useReplayTick({ getWsClient: () => null }),
    )

    act(() => {
      useReplayStore.getState().setPhase('paused')
    })
    rerender()

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(useReplayStore.getState().trailBars).toHaveLength(0)
    expect(useReplayStore.getState().tickQueue).toHaveLength(2)
  })
})
