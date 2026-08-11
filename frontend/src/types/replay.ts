import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap, IndicatorSpec } from '@/types/indicator'

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

export type ReplayConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'amber'
  | 'red'
  | 'closed'

export type ReplayConnectionReason =
  | 'unauthorized'
  | 'superseded'
  | 'not_found'
  | 'error'
  | null

export type ReplaySpeed = 0.5 | 1 | 2 | 5 | 10

export type ReplayServerState = 'idle' | 'playing' | 'paused' | 'completed'

export interface ReplayTick {
  bar: OHLCVBar
  indicators: Record<string, IndicatorPoint>
}

export interface ReplaySnapshot {
  bars: OHLCVBar[]
  indicators: IndicatorSeriesMap
  cursor: number | null
  startAnchor: number
  latestAvailable: number | null
}

export interface ReplaySessionMeta {
  sessionId: string
  symbol: string
  timeframe: string
  stepTimeframe: string
  startAnchor: number
  latestAvailable: number | null
  cursor: number | null
  serverState: ReplayServerState
  speed: number
  barIndex: number
  queueRemaining: number
  indicators: IndicatorSpec[]
}

export interface ReplayCreateResponse {
  sessionId: string
  wsUrl: string
}

export interface ReplayCreateBody {
  symbol: string
  timeframe: string
  start: number
  indicators: IndicatorSpec[]
  speed: number
  autoplay: boolean
}

/** Client → server WS commands */
export type ReplayWsOutbound =
  | { action: 'play'; speed?: number }
  | { action: 'pause' }
  | { action: 'step'; count: number }
  | { action: 'seek'; to: number }
  | { action: 'set_speed'; speed: number }
  | { action: 'refill' }
  | { action: 'set_indicators'; indicators: IndicatorSpec[] }
  | { action: 'get_state' }

/** Server → client WS events (normalized) */
export type ReplayWsInbound =
  | ({ type: 'replay_state' } & ReplaySessionMeta)
  | ({ type: 'snapshot' } & ReplaySnapshot)
  | {
      type: 'tick_batch'
      ticks: ReplayTick[]
      cursor: number | null
      queueRemaining: number
    }
  | { type: 'buffer_loading' }
  | {
      type: 'buffer_ready'
      bufferEnd: number | null
      latestAvailable: number | null
    }
  | { type: 'buffer_reset' }
  | { type: 'replay_completed' }
  | { type: 'error'; code: string; message: string }
