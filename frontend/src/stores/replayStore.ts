import { create } from 'zustand'
import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap } from '@/types/indicator'
import type {
  ReplayConnectionStatus,
  ReplayPhase,
  ReplayServerState,
  ReplaySnapshotEvent,
  ReplayStateResponse,
  ReplayTick,
  ReplayTickBatchEvent,
} from '@/types/replay'
import type { ReplayWsClient } from '@/services/replayWsClient'
import {
  filterIndicatorsBefore,
  filterIndicatorsFrom,
} from '@/utils/replayChartData'

function mergeIndicatorPoint(
  map: IndicatorSeriesMap,
  seriesId: string,
  point: IndicatorPoint,
): IndicatorSeriesMap {
  const existing = map[seriesId] ?? []
  const last = existing[existing.length - 1]
  if (last?.time === point.time) {
    const next = [...existing]
    next[next.length - 1] = point
    return { ...map, [seriesId]: next }
  }
  return { ...map, [seriesId]: [...existing, point] }
}

function mergeIndicatorSeries(
  map: IndicatorSeriesMap,
  series: Record<string, IndicatorPoint[]>,
): IndicatorSeriesMap {
  let next = { ...map }
  for (const [seriesId, points] of Object.entries(series)) {
    next[seriesId] = points
  }
  return next
}

function truncateToCursor(
  candles: OHLCVBar[],
  indicators: IndicatorSeriesMap,
  cursor: number | null,
): { candles: OHLCVBar[]; indicators: IndicatorSeriesMap } {
  if (cursor == null) {
    return { candles: [], indicators: {} }
  }
  const nextCandles = candles.filter((bar) => bar.time <= cursor)
  const nextIndicators: IndicatorSeriesMap = {}
  for (const [seriesId, points] of Object.entries(indicators)) {
    nextIndicators[seriesId] = points.filter((point) => point.time <= cursor)
  }
  return { candles: nextCandles, indicators: nextIndicators }
}

function ticksFromBatch(batch: ReplayTickBatchEvent): ReplayTick[] {
  return batch.ticks.map((tick) => ({
    bar: tick.bar,
    indicators: Object.fromEntries(
      Object.entries(tick.indicators).map(([key, value]) => [
        key,
        {
          time: value.time ?? tick.bar.time,
          value: value.value ?? null,
        },
      ]),
    ),
  }))
}

interface ReplayStoreState {
  phase: ReplayPhase
  sessionId: string | null
  wsClient: ReplayWsClient | null
  serverState: ReplayServerState
  connectionStatus: ReplayConnectionStatus
  connectionMessage: string | null
  speed: number
  cursor: number | null
  startAnchor: number | null
  latestAvailable: number | null
  queueRemaining: number
  tickQueue: ReplayTick[]
  baselineCandles: OHLCVBar[]
  baselineIndicators: IndicatorSeriesMap
  candles: OHLCVBar[]
  indicators: IndicatorSeriesMap
  bufferLoading: boolean
  followReplay: boolean
  pendingSeekCursor: number | null

  enterPickAnchor: () => void
  setInactive: () => void
  setConnecting: (sessionId: string) => void
  attachWsClient: (client: ReplayWsClient) => void
  applyState: (state: ReplayStateResponse | Partial<ReplayStateResponse>) => void
  applySnapshot: (snapshot: ReplaySnapshotEvent) => void
  setReplayBaseline: (candles: OHLCVBar[], indicators: IndicatorSeriesMap) => void
  enqueueBatch: (batch: ReplayTickBatchEvent) => void
  shiftTick: () => ReplayTick | undefined
  applyTick: (tick: ReplayTick) => void
  setBufferLoading: (loading: boolean) => void
  setCompleted: () => void
  setConnectionStatus: (status: ReplayConnectionStatus, message?: string | null) => void
  setSpeed: (speed: number) => void
  setPhase: (phase: ReplayPhase) => void
  pauseLocally: () => void
  playLocally: () => void
  beginSeek: (to: number) => void
  snapSeekToCursor: () => void
  resetSession: () => void
  setFollowReplay: (follow: boolean) => void
}

const idleSession = {
  phase: 'inactive' as const,
  sessionId: null as string | null,
  wsClient: null as ReplayWsClient | null,
  serverState: 'paused' as ReplayServerState,
  connectionStatus: 'disconnected' as ReplayConnectionStatus,
  connectionMessage: null as string | null,
  speed: 1,
  cursor: null as number | null,
  startAnchor: null as number | null,
  latestAvailable: null as number | null,
  queueRemaining: 0,
  tickQueue: [] as ReplayTick[],
  baselineCandles: [] as OHLCVBar[],
  baselineIndicators: {} as IndicatorSeriesMap,
  candles: [] as OHLCVBar[],
  indicators: {} as IndicatorSeriesMap,
  bufferLoading: false,
  followReplay: true,
  pendingSeekCursor: null as number | null,
}

export const useReplayStore = create<ReplayStoreState>((set, get) => ({
  ...idleSession,

  enterPickAnchor: () =>
    set({
      ...idleSession,
      phase: 'pick_anchor',
    }),

  setInactive: () => {
    const { wsClient } = get()
    wsClient?.disconnect()
    set({ ...idleSession })
  },

  setConnecting: (sessionId) =>
    set({
      phase: 'connecting',
      sessionId,
      connectionStatus: 'disconnected',
      connectionMessage: null,
    }),

  attachWsClient: (client) => set({ wsClient: client }),

  applyState: (state) =>
    set((prev) => {
      const cursor = state.cursor ?? prev.cursor
      const truncated =
        cursor != null && prev.cursor != null && cursor < prev.cursor
          ? truncateToCursor(prev.candles, prev.indicators, cursor)
          : { candles: prev.candles, indicators: prev.indicators }

      let phase = prev.phase
      if (state.state === 'completed') {
        phase = 'completed'
      } else if (state.state === 'playing' && prev.phase !== 'seeking' && prev.phase !== 'connecting') {
        phase = 'playing'
      } else if (state.state === 'paused' && prev.phase === 'seeking') {
        phase = 'paused'
      }

      return {
        cursor,
        startAnchor: state.startAnchor ?? prev.startAnchor,
        latestAvailable: state.latestAvailable ?? prev.latestAvailable,
        queueRemaining: state.queueRemaining ?? prev.queueRemaining,
        serverState: state.state ?? prev.serverState,
        speed: state.speed ?? prev.speed,
        candles: truncated.candles,
        indicators: truncated.indicators,
        phase,
        pendingSeekCursor: phase === 'paused' && prev.phase === 'seeking' ? null : prev.pendingSeekCursor,
      }
    }),

  applySnapshot: (snapshot) =>
    set((prev) => {
      const startAnchor = snapshot.startAnchor ?? prev.startAnchor
      const next: Partial<ReplayStoreState> = {
        cursor: snapshot.cursor,
        startAnchor,
        latestAvailable: snapshot.latestAvailable,
        tickQueue: [],
        phase: 'ready',
        serverState: 'paused',
        bufferLoading: false,
        pendingSeekCursor: null,
      }

      if (snapshot.bars.length > 0 && startAnchor != null) {
        next.baselineCandles = snapshot.bars.filter((bar) => bar.time < startAnchor)
        next.candles = snapshot.bars.filter((bar) => bar.time >= startAnchor)
        next.baselineIndicators = filterIndicatorsBefore(startAnchor, snapshot.indicators)
        next.indicators = filterIndicatorsFrom(startAnchor, snapshot.indicators)
      } else if (snapshot.bars.length > 0) {
        next.candles = snapshot.bars
        next.indicators = mergeIndicatorSeries({}, snapshot.indicators)
      }

      return { ...prev, ...next }
    }),

  setReplayBaseline: (candles, indicators) =>
    set({
      baselineCandles: candles,
      baselineIndicators: indicators,
    }),

  enqueueBatch: (batch) =>
    set((prev) => ({
      tickQueue: [...prev.tickQueue, ...ticksFromBatch(batch)],
      cursor: batch.cursor ?? prev.cursor,
      queueRemaining: batch.queueRemaining ?? prev.queueRemaining,
      latestAvailable: prev.latestAvailable,
    })),

  shiftTick: () => {
    const { tickQueue } = get()
    if (tickQueue.length === 0) {
      return undefined
    }
    const [next, ...rest] = tickQueue
    set({ tickQueue: rest })
    return next
  },

  applyTick: (tick) =>
    set((prev) => {
      let indicators = prev.indicators
      for (const [seriesId, point] of Object.entries(tick.indicators)) {
        indicators = mergeIndicatorPoint(indicators, seriesId, point)
      }

      const last = prev.candles[prev.candles.length - 1]
      const candles =
        last?.time === tick.bar.time
          ? [...prev.candles.slice(0, -1), tick.bar]
          : [...prev.candles, tick.bar]

      return {
        candles,
        indicators,
        cursor: tick.bar.time,
      }
    }),

  setBufferLoading: (loading) =>
    set((prev) => ({
      bufferLoading: loading,
      phase: loading ? 'buffer_loading' : prev.phase === 'buffer_loading' ? 'playing' : prev.phase,
    })),

  setCompleted: () =>
    set({
      phase: 'completed',
      serverState: 'completed',
      tickQueue: [],
      bufferLoading: false,
    }),

  setConnectionStatus: (status, message = null) =>
    set({ connectionStatus: status, connectionMessage: message }),

  setSpeed: (speed) => set({ speed }),

  setPhase: (phase) => set({ phase }),

  pauseLocally: () =>
    set((prev) => ({
      phase: prev.phase === 'completed' ? 'completed' : 'paused',
    })),

  playLocally: () =>
    set((prev) => ({
      phase: prev.phase === 'completed' ? 'completed' : 'playing',
    })),

  beginSeek: (to) =>
    set({
      pendingSeekCursor: to,
      phase: 'seeking',
    }),

  snapSeekToCursor: () =>
    set((prev) => ({
      pendingSeekCursor: prev.cursor,
      phase: prev.phase === 'seeking' ? 'paused' : prev.phase,
    })),

  resetSession: () => {
    const { wsClient } = get()
    wsClient?.disconnect()
    set({ ...idleSession })
  },

  setFollowReplay: (follow) => set({ followReplay: follow }),
}))
