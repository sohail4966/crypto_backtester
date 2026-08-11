import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReplayStore } from '@/stores/replayStore'
import type { ReplaySessionMeta, ReplayTick } from '@/types/replay'

const baseMeta = (overrides: Partial<ReplaySessionMeta> = {}): ReplaySessionMeta => ({
  sessionId: 's1',
  symbol: 'BTC/USDT',
  timeframe: '1h',
  stepTimeframe: '1h',
  startAnchor: 100,
  latestAvailable: 500,
  cursor: 90,
  serverState: 'paused',
  speed: 1,
  barIndex: 0,
  queueRemaining: 100,
  indicators: [],
  ...overrides,
})

const tick = (time: number): ReplayTick => ({
  bar: { time, open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 },
  indicators: { EMA_20: { time, value: 1.1 } },
})

describe('replayStore', () => {
  beforeEach(() => {
    useReplayStore.getState().reset()
  })

  it('transitions pick_anchor → connecting → paused → playing → paused → completed', () => {
    const store = useReplayStore.getState()
    store.enterPickAnchor()
    expect(useReplayStore.getState().phase).toBe('pick_anchor')

    store.beginConnect('s1', '/ws/replay/s1')
    expect(useReplayStore.getState().phase).toBe('connecting')

    store.applyReplayState(baseMeta())
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    expect(useReplayStore.getState().phase).toBe('paused')
    expect(useReplayStore.getState().trailBars).toEqual([])
    expect(useReplayStore.getState().trailAuthoritative).toBe(true)

    store.setPhase('playing')
    expect(useReplayStore.getState().phase).toBe('playing')
    store.setPhase('paused')
    store.markCompleted()
    expect(useReplayStore.getState().phase).toBe('completed')
  })

  it('first drain reveals anchor after empty snapshot', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta())
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks([tick(100)], { cursor: 100, queueRemaining: 99 })
    const drained = useReplayStore.getState().drainOne()
    expect(drained?.bar.time).toBe(100)
    expect(useReplayStore.getState().trailBars).toHaveLength(1)
    expect(useReplayStore.getState().trailBars[0]?.time).toBe(100)
  })

  it('step path applies immediately without double-drain', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.markExpectImmediateTicks()
    store.enqueueTicks([tick(100)], { cursor: 100, queueRemaining: 99 })
    expect(useReplayStore.getState().tickQueue).toHaveLength(0)
    expect(useReplayStore.getState().trailBars).toHaveLength(1)
    expect(useReplayStore.getState().drainOne()).toBeNull()
  })

  it('in-window seek slices trail', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [tick(100).bar, tick(200).bar, tick(300).bar],
      indicators: {
        EMA_20: [
          { time: 100, value: 1 },
          { time: 200, value: 2 },
          { time: 300, value: 3 },
        ],
      },
      cursor: 300,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.applyReplayState(baseMeta({ cursor: 200 }), { sliceTrail: true })
    expect(useReplayStore.getState().trailBars.map((b) => b.time)).toEqual([
      100, 200,
    ])
    expect(useReplayStore.getState().trailIndicators.EMA_20?.map((p) => p.time)).toEqual([
      100, 200,
    ])
  })

  it('snapshot replace clears queue and rebuilds trail', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [tick(100).bar],
      indicators: {},
      cursor: 100,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks([tick(200), tick(300)])
    expect(useReplayStore.getState().tickQueue).toHaveLength(2)
    store.applySnapshot({
      bars: [tick(150).bar],
      indicators: {},
      cursor: 150,
      startAnchor: 100,
      latestAvailable: 500,
    })
    expect(useReplayStore.getState().tickQueue).toHaveLength(0)
    expect(useReplayStore.getState().trailBars[0]?.time).toBe(150)
  })

  it('enqueueTicks does not advance revealed cursor (server prefetch tip)', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta({ cursor: 90 }))
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks([tick(100), tick(200)], { cursor: 200, queueRemaining: 80 })
    expect(useReplayStore.getState().meta?.cursor).toBe(90)
    expect(useReplayStore.getState().meta?.queueRemaining).toBe(80)
    expect(useReplayStore.getState().tickQueue).toHaveLength(2)
  })

  it('defers completed until local queue drains', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta({ cursor: 90 }))
    store.applySnapshot({
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.enqueueTicks([tick(100), tick(200)])
    store.setPhase('playing')
    store.markCompleted()
    expect(useReplayStore.getState().phase).toBe('playing')
    expect(useReplayStore.getState().pendingCompleted).toBe(true)

    store.drainOne()
    expect(useReplayStore.getState().phase).toBe('playing')
    store.drainOne()
    expect(useReplayStore.getState().phase).toBe('completed')
    expect(useReplayStore.getState().pendingCompleted).toBe(false)
    expect(useReplayStore.getState().trailBars).toHaveLength(2)
  })

  it('applyReplayState preserves client cursor while trail is authoritative', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta({ cursor: 90 }))
    store.applySnapshot({
      bars: [tick(100).bar],
      indicators: {},
      cursor: 100,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.setPhase('playing')
    store.applyReplayState(baseMeta({ cursor: 400, queueRemaining: 10, serverState: 'playing' }))
    expect(useReplayStore.getState().meta?.cursor).toBe(100)
    expect(useReplayStore.getState().meta?.queueRemaining).toBe(10)
  })

  it('SEEK_OUT_OF_RANGE path leaves cursor when error handled externally', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta({ cursor: 200 }))
    store.applySnapshot({
      bars: [tick(200).bar],
      indicators: {},
      cursor: 200,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.beginSeeking()
    store.markAwaitingSnapshotReplace()
    store.cancelSeek()
    expect(useReplayStore.getState().phase).toBe('paused')
    expect(useReplayStore.getState().awaitingSnapshotReplace).toBe(false)
    expect(useReplayStore.getState().meta?.cursor).toBe(200)
  })

  it('oob seek keeps seeking until snapshot while awaiting replace', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applyReplayState(baseMeta({ cursor: 200 }))
    store.applySnapshot({
      bars: [tick(200).bar],
      indicators: {},
      cursor: 200,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.beginSeeking()
    store.markAwaitingSnapshotReplace()
    store.applyReplayState(baseMeta({ cursor: 450 }))
    expect(useReplayStore.getState().phase).toBe('seeking')
    expect(useReplayStore.getState().meta?.cursor).toBe(200)
    store.applySnapshot({
      bars: [tick(100).bar, tick(450).bar],
      indicators: {},
      cursor: 450,
      startAnchor: 100,
      latestAvailable: 500,
    })
    expect(useReplayStore.getState().phase).toBe('paused')
    expect(useReplayStore.getState().meta?.cursor).toBe(450)
    expect(useReplayStore.getState().trailBars).toHaveLength(2)
  })

  it('buffer timeout restores prior phase', () => {
    vi.useFakeTimers()
    const store = useReplayStore.getState()
    store.setPhase('playing')
    store.beginBufferLoading()
    expect(useReplayStore.getState().phase).toBe('buffer_loading')
    store.timeoutBufferLoading()
    expect(useReplayStore.getState().phase).toBe('playing')
    vi.useRealTimers()
  })

  it('reset clears session fields', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.setSpeed(5)
    store.reset()
    expect(useReplayStore.getState().sessionId).toBeNull()
    expect(useReplayStore.getState().phase).toBe('inactive')
    expect(useReplayStore.getState().speed).toBe(5)
  })

  it('seeking earlier from completed → paused', () => {
    const store = useReplayStore.getState()
    store.beginConnect('s1', '/ws/replay/s1')
    store.applySnapshot({
      bars: [tick(100).bar, tick(500).bar],
      indicators: {},
      cursor: 500,
      startAnchor: 100,
      latestAvailable: 500,
    })
    store.markCompleted()
    store.applyReplayState(baseMeta({ cursor: 100, latestAvailable: 500 }), {
      sliceTrail: true,
    })
    expect(useReplayStore.getState().phase).toBe('paused')
  })
})
