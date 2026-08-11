import { create } from 'zustand'
import type { OHLCVBar } from '@/types/candle'
import type { IndicatorSeriesMap } from '@/types/indicator'
import type {
  ReplayConnectionReason,
  ReplayConnectionStatus,
  ReplayPhase,
  ReplaySessionMeta,
  ReplaySnapshot,
  ReplaySpeed,
  ReplayTick,
} from '@/types/replay'

type TransportPhase = 'playing' | 'paused'

function appendTickToTrail(
  bars: OHLCVBar[],
  indicators: IndicatorSeriesMap,
  tick: ReplayTick,
): { bars: OHLCVBar[]; indicators: IndicatorSeriesMap } {
  const nextBars = [...bars, tick.bar]
  const nextIndicators: IndicatorSeriesMap = { ...indicators }
  for (const [key, point] of Object.entries(tick.indicators)) {
    const series = nextIndicators[key] ? [...nextIndicators[key]] : []
    const last = series[series.length - 1]
    if (last && last.time === point.time) {
      series[series.length - 1] = point
    } else {
      series.push(point)
    }
    nextIndicators[key] = series
  }
  return { bars: nextBars, indicators: nextIndicators }
}

function sliceTrailToCursor(
  bars: OHLCVBar[],
  indicators: IndicatorSeriesMap,
  cursor: number | null,
): { bars: OHLCVBar[]; indicators: IndicatorSeriesMap } {
  if (cursor == null) {
    return { bars: [], indicators: {} }
  }
  const nextBars = bars.filter((bar) => bar.time <= cursor)
  const nextIndicators: IndicatorSeriesMap = {}
  for (const [key, points] of Object.entries(indicators)) {
    nextIndicators[key] = points.filter((point) => point.time <= cursor)
  }
  return { bars: nextBars, indicators: nextIndicators }
}

interface ReplayState {
  phase: ReplayPhase
  sessionId: string | null
  wsUrl: string | null
  meta: ReplaySessionMeta | null
  tickQueue: ReplayTick[]
  trailBars: OHLCVBar[]
  trailIndicators: IndicatorSeriesMap
  /** True after first snapshot received for the active session. */
  trailAuthoritative: boolean
  speed: ReplaySpeed
  followReplay: true
  connection: ReplayConnectionStatus
  connectionReason: ReplayConnectionReason
  bufferLoadingSince: number | null
  phaseBeforeBuffer: TransportPhase | null
  errorMessage: string | null
  /** When true, next tick_batch applies immediately (step path). */
  expectImmediateTicks: boolean
  /** After set_indicators until user Play — ignore server playing. */
  forcePausedUntilPlay: boolean
  /** Out-of-window seek: wait for snapshot before applying replay_state. */
  awaitingSnapshotReplace: boolean
  needsRefill: boolean
  /** Server signaled completed; wait until local queue is drained. */
  pendingCompleted: boolean

  enterPickAnchor: () => void
  beginConnect: (sessionId: string, wsUrl: string) => void
  applyReplayState: (meta: ReplaySessionMeta, options?: { sliceTrail?: boolean }) => void
  applySnapshot: (snapshot: ReplaySnapshot) => void
  enqueueTicks: (
    ticks: ReplayTick[],
    meta?: { cursor?: number | null; queueRemaining?: number },
  ) => void
  applyTicksImmediate: (
    ticks: ReplayTick[],
    meta?: { cursor?: number | null; queueRemaining?: number },
  ) => void
  drainOne: () => ReplayTick | null
  setPhase: (phase: ReplayPhase) => void
  setSpeed: (speed: ReplaySpeed) => void
  setConnection: (
    status: ReplayConnectionStatus,
    reason?: ReplayConnectionReason,
  ) => void
  clearQueue: () => void
  markExpectImmediateTicks: () => void
  clearExpectImmediateTicks: () => void
  beginSeeking: () => void
  cancelSeek: () => void
  markAwaitingSnapshotReplace: () => void
  beginBufferLoading: () => void
  endBufferLoading: () => void
  timeoutBufferLoading: () => void
  markCompleted: () => void
  setError: (message: string) => void
  setForcePausedUntilPlay: (value: boolean) => void
  reset: () => void
  resetToPickAnchor: () => void
}

const initialState = {
  phase: 'inactive' as ReplayPhase,
  sessionId: null as string | null,
  wsUrl: null as string | null,
  meta: null as ReplaySessionMeta | null,
  tickQueue: [] as ReplayTick[],
  trailBars: [] as OHLCVBar[],
  trailIndicators: {} as IndicatorSeriesMap,
  trailAuthoritative: false,
  speed: 1 as ReplaySpeed,
  followReplay: true as const,
  connection: 'idle' as ReplayConnectionStatus,
  connectionReason: null as ReplayConnectionReason,
  bufferLoadingSince: null as number | null,
  phaseBeforeBuffer: null as TransportPhase | null,
  errorMessage: null as string | null,
  expectImmediateTicks: false,
  forcePausedUntilPlay: false,
  awaitingSnapshotReplace: false,
  needsRefill: false,
  pendingCompleted: false,
}

function isReplaySpeed(value: number): value is ReplaySpeed {
  return value === 0.5 || value === 1 || value === 2 || value === 5 || value === 10
}

export const useReplayStore = create<ReplayState>((set, get) => ({
  ...initialState,

  enterPickAnchor: () =>
    set({
      ...initialState,
      phase: 'pick_anchor',
      speed: get().speed,
    }),

  beginConnect: (sessionId, wsUrl) =>
    set({
      phase: 'connecting',
      sessionId,
      wsUrl,
      meta: null,
      tickQueue: [],
      trailBars: [],
      trailIndicators: {},
      trailAuthoritative: false,
      connection: 'connecting',
      connectionReason: null,
      bufferLoadingSince: null,
      phaseBeforeBuffer: null,
      errorMessage: null,
      expectImmediateTicks: false,
      forcePausedUntilPlay: false,
      awaitingSnapshotReplace: false,
      needsRefill: false,
      pendingCompleted: false,
    }),

  applyReplayState: (meta, options) => {
    const state = get()
    let trailBars = state.trailBars
    let trailIndicators = state.trailIndicators

    if (options?.sliceTrail && state.trailAuthoritative) {
      const sliced = sliceTrailToCursor(
        state.trailBars,
        state.trailIndicators,
        meta.cursor,
      )
      trailBars = sliced.bars
      trailIndicators = sliced.indicators
    }

    const speed = isReplaySpeed(meta.speed) ? meta.speed : state.speed

    // Server cursor after tick_batch/refill is the prefetch tip. Scrubber/trail
    // must track the client-revealed cursor until seek or pre-trail connect.
    // While awaiting an oob snapshot, keep the last valid client cursor.
    const useServerCursor =
      options?.sliceTrail === true ||
      !state.trailAuthoritative ||
      state.phase === 'connecting' ||
      (state.phase === 'seeking' && !state.awaitingSnapshotReplace)

    const mergedMeta: ReplaySessionMeta = {
      ...meta,
      cursor: useServerCursor ? meta.cursor : (state.meta?.cursor ?? meta.cursor),
    }

    const queueAfter = options?.sliceTrail ? [] : state.tickQueue
    let phase = state.phase
    let pendingCompleted = state.pendingCompleted

    if (state.forcePausedUntilPlay) {
      phase = 'paused'
    } else if (
      state.phase === 'completed' &&
      options?.sliceTrail &&
      mergedMeta.cursor != null &&
      mergedMeta.latestAvailable != null &&
      mergedMeta.cursor < mergedMeta.latestAvailable
    ) {
      phase = 'paused'
      pendingCompleted = false
    } else if (meta.serverState === 'completed' && state.phase !== 'seeking') {
      if (queueAfter.length > 0) {
        pendingCompleted = true
      } else {
        phase = 'completed'
        pendingCompleted = false
      }
    } else if (
      (state.phase === 'seeking' && !state.awaitingSnapshotReplace) ||
      state.phase === 'connecting' ||
      state.phase === 'ready'
    ) {
      phase = 'paused'
    }

    set({
      meta: mergedMeta,
      speed,
      trailBars,
      trailIndicators,
      phase,
      tickQueue: queueAfter,
      pendingCompleted,
    })
  },

  applySnapshot: (snapshot) => {
    const state = get()
    const meta = state.meta
      ? {
          ...state.meta,
          cursor: snapshot.cursor,
          startAnchor: snapshot.startAnchor,
          latestAvailable: snapshot.latestAvailable,
        }
      : state.meta

    let phase: ReplayPhase = state.phase
    if (
      state.phase === 'connecting' ||
      state.phase === 'seeking' ||
      state.phase === 'ready'
    ) {
      phase = 'paused'
    }
    if (state.forcePausedUntilPlay) {
      phase = 'paused'
    }

    set({
      trailBars: snapshot.bars,
      trailIndicators: snapshot.indicators,
      trailAuthoritative: true,
      tickQueue: [],
      meta,
      phase,
      awaitingSnapshotReplace: false,
      needsRefill: false,
    })
  },

  enqueueTicks: (ticks, metaUpdate) => {
    if (ticks.length === 0 && !metaUpdate) {
      return
    }
    const state = get()
    if (state.expectImmediateTicks) {
      get().applyTicksImmediate(ticks, metaUpdate)
      return
    }
    set((prev) => {
      const tickQueue = [...prev.tickQueue, ...ticks]
      // Do not adopt batch cursor — that is the server prefetch tip.
      const meta =
        prev.meta && metaUpdate?.queueRemaining !== undefined
          ? {
              ...prev.meta,
              queueRemaining: metaUpdate.queueRemaining,
            }
          : prev.meta
      return {
        tickQueue,
        meta,
        needsRefill: tickQueue.length < 20,
      }
    })
  },

  applyTicksImmediate: (ticks, metaUpdate) => {
    set((prev) => {
      let bars = prev.trailBars
      let indicators = prev.trailIndicators
      for (const tick of ticks) {
        const next = appendTickToTrail(bars, indicators, tick)
        bars = next.bars
        indicators = next.indicators
      }
      const lastBar = ticks[ticks.length - 1]?.bar
      const meta =
        prev.meta
          ? {
              ...prev.meta,
              cursor:
                metaUpdate?.cursor !== undefined
                  ? metaUpdate.cursor
                  : (lastBar?.time ?? prev.meta.cursor),
              queueRemaining:
                metaUpdate?.queueRemaining !== undefined
                  ? metaUpdate.queueRemaining
                  : prev.meta.queueRemaining,
            }
          : prev.meta
      return {
        trailBars: bars,
        trailIndicators: indicators,
        meta,
        expectImmediateTicks: false,
        needsRefill: prev.tickQueue.length < 20,
      }
    })
  },

  drainOne: () => {
    const state = get()
    const [next, ...rest] = state.tickQueue
    if (!next) {
      set({ needsRefill: true })
      return null
    }
    const { bars, indicators } = appendTickToTrail(
      state.trailBars,
      state.trailIndicators,
      next,
    )
    const becomeCompleted = rest.length === 0 && state.pendingCompleted
    set({
      tickQueue: rest,
      trailBars: bars,
      trailIndicators: indicators,
      meta: state.meta
        ? {
            ...state.meta,
            cursor: next.bar.time,
            queueRemaining: Math.max(0, state.meta.queueRemaining - 1),
            serverState: becomeCompleted ? 'completed' : state.meta.serverState,
          }
        : state.meta,
      needsRefill: rest.length < 20,
      pendingCompleted: becomeCompleted ? false : state.pendingCompleted,
      phase: becomeCompleted ? 'completed' : state.phase,
    })
    return next
  },

  setPhase: (phase) => set({ phase }),

  setSpeed: (speed) => set({ speed }),

  setConnection: (status, reason = null) =>
    set({ connection: status, connectionReason: reason }),

  clearQueue: () =>
    set({ tickQueue: [], needsRefill: true, expectImmediateTicks: false }),

  markExpectImmediateTicks: () => set({ expectImmediateTicks: true }),

  clearExpectImmediateTicks: () => set({ expectImmediateTicks: false }),

  beginSeeking: () =>
    set({ phase: 'seeking', expectImmediateTicks: false, pendingCompleted: false }),

  cancelSeek: () =>
    set({
      phase: 'paused',
      awaitingSnapshotReplace: false,
      expectImmediateTicks: false,
    }),

  markAwaitingSnapshotReplace: () => set({ awaitingSnapshotReplace: true }),

  beginBufferLoading: () => {
    const state = get()
    const prior: TransportPhase =
      state.phase === 'playing' ? 'playing' : 'paused'
    set({
      phase: 'buffer_loading',
      bufferLoadingSince: Date.now(),
      phaseBeforeBuffer:
        state.phase === 'buffer_loading'
          ? state.phaseBeforeBuffer
          : prior,
    })
  },

  endBufferLoading: () => {
    const state = get()
    const restore = state.phaseBeforeBuffer ?? 'paused'
    set({
      phase: state.forcePausedUntilPlay ? 'paused' : restore,
      bufferLoadingSince: null,
      phaseBeforeBuffer: null,
    })
  },

  timeoutBufferLoading: () => {
    const state = get()
    if (state.phase !== 'buffer_loading') {
      return
    }
    const restore = state.phaseBeforeBuffer ?? 'paused'
    set({
      phase: state.forcePausedUntilPlay ? 'paused' : restore,
      bufferLoadingSince: null,
      phaseBeforeBuffer: null,
    })
  },

  markCompleted: () => {
    const state = get()
    if (state.tickQueue.length > 0) {
      set({ pendingCompleted: true })
      return
    }
    set({
      phase: 'completed',
      pendingCompleted: false,
      meta: state.meta
        ? { ...state.meta, serverState: 'completed' }
        : state.meta,
    })
  },

  setError: (message) =>
    set({
      phase: 'error',
      errorMessage: message,
      connection: 'red',
      connectionReason: 'error',
      expectImmediateTicks: false,
    }),

  setForcePausedUntilPlay: (value) => set({ forcePausedUntilPlay: value }),

  reset: () => set({ ...initialState, speed: get().speed }),

  resetToPickAnchor: () =>
    set({
      ...initialState,
      phase: 'pick_anchor',
      speed: get().speed,
    }),
}))

export function sessionActivePhase(phase: ReplayPhase): boolean {
  return (
    phase === 'connecting' ||
    phase === 'ready' ||
    phase === 'playing' ||
    phase === 'paused' ||
    phase === 'seeking' ||
    phase === 'buffer_loading' ||
    phase === 'completed'
  )
}
