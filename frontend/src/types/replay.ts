import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSpec } from '@/types/indicator'

export type ReplayPhase =
  | 'inactive'
  | 'pick_anchor'
  | 'connecting'
  | 'ready'
  | 'playing'
  | 'paused'
  | 'seeking'
  | 'buffer_loading'
  | 'completed'
  | 'error'

export type ReplayServerState = 'idle' | 'playing' | 'paused' | 'completed'

export type ReplayConnectionStatus = 'disconnected' | 'connected' | 'superseded' | 'not_found' | 'error'

export interface ReplayTick {
  bar: OHLCVBar
  indicators: Record<string, IndicatorPoint>
}

export interface ReplaySessionCreateRequest {
  symbol: string
  timeframe: string
  start: number
  indicators: IndicatorSpec[]
  step_timeframe?: string | null
  speed?: number
}

export interface ReplaySessionCreateResponse {
  sessionId: string
  wsUrl: string
}

export interface ReplayStateResponse {
  sessionId: string
  symbol: string
  timeframe: string
  stepTimeframe: string
  startAnchor: number
  latestAvailable: number | null
  cursor: number | null
  state: ReplayServerState
  speed: number
  barIndex: number
  queueRemaining: number
  indicators: IndicatorSpec[]
}

export interface ReplaySnapshotEvent {
  type: 'snapshot'
  bars: OHLCVBar[]
  indicators: Record<string, IndicatorPoint[]>
  cursor: number | null
  startAnchor: number
  latestAvailable: number | null
}

export interface ReplayStateEvent {
  type: 'replay_state'
  sessionId?: string
  symbol?: string
  timeframe?: string
  stepTimeframe?: string
  startAnchor?: number
  latestAvailable?: number | null
  cursor?: number | null
  state?: ReplayServerState
  speed?: number
  barIndex?: number
  queueRemaining?: number
  indicators?: IndicatorSpec[]
}

export interface ReplayTickBatchEvent {
  type: 'tick_batch'
  ticks: ReplayTick[]
  cursor: number | null
  queueRemaining: number
}

export interface ReplayBufferLoadingEvent {
  type: 'buffer_loading'
}

export interface ReplayBufferReadyEvent {
  type: 'buffer_ready'
  bufferEnd?: number | null
  latestAvailable?: number | null
}

export interface ReplayBufferResetEvent {
  type: 'buffer_reset'
}

export interface ReplayCompletedEvent {
  type: 'replay_completed'
}

export interface ReplayErrorEvent {
  type: 'error'
  code: string
  message: string
}

export type ReplayServerEvent =
  | ReplaySnapshotEvent
  | ReplayStateEvent
  | ReplayTickBatchEvent
  | ReplayBufferLoadingEvent
  | ReplayBufferReadyEvent
  | ReplayBufferResetEvent
  | ReplayCompletedEvent
  | ReplayErrorEvent

export type ReplayWsCommand =
  | { action: 'play'; speed?: number }
  | { action: 'pause' }
  | { action: 'step'; count?: number }
  | { action: 'seek'; to: number }
  | { action: 'set_speed'; speed: number }
  | { action: 'refill' }
  | { action: 'set_indicators'; indicators: IndicatorSpec[] }
  | { action: 'get_state' }

export const REPLAY_TICK_REFILL_THRESHOLD = 20
export const REPLAY_BUFFER_LOADING_TIMEOUT_MS = 3000
export const REPLAY_INTERVAL_MS_MIN = 50
export const REPLAY_GHOST_OPACITY = 0.25
export const REPLAY_SPEED_OPTIONS = [0.1, 0.5, 1, 2, 5, 10, 20] as const

export function replayIntervalMs(speed: number): number {
  const safe = speed > 0 ? speed : 1
  return Math.max(REPLAY_INTERVAL_MS_MIN, 1000 / safe)
}

export function replayProgress(
  cursor: number | null,
  startAnchor: number | null,
  latestAvailable: number | null,
): number {
  if (cursor == null || startAnchor == null || latestAvailable == null) {
    return 0
  }
  const span = latestAvailable - startAnchor
  if (span <= 0) {
    return cursor >= startAnchor ? 1 : 0
  }
  return Math.min(1, Math.max(0, (cursor - startAnchor) / span))
}
