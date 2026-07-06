import { apiRequest } from '@/services/api'
import type {
  ReplaySessionCreateRequest,
  ReplaySessionCreateResponse,
  ReplayStateResponse,
} from '@/types/replay'

interface RawSessionCreateResponse {
  session_id?: string
  sessionId?: string
  ws_url?: string
  wsUrl?: string
}

interface RawStateResponse {
  session_id?: string
  sessionId?: string
  symbol?: string
  timeframe?: string
  step_timeframe?: string
  stepTimeframe?: string
  start?: number
  startAnchor?: number
  latest_available?: number | null
  latestAvailable?: number | null
  cursor?: number | null
  state?: ReplayStateResponse['state']
  speed?: number
  bar_index?: number
  barIndex?: number
  queue_remaining?: number
  queueRemaining?: number
  indicators?: ReplayStateResponse['indicators']
}

function normalizeCreateResponse(raw: RawSessionCreateResponse): ReplaySessionCreateResponse {
  const sessionId = raw.sessionId ?? raw.session_id
  const wsUrl = raw.wsUrl ?? raw.ws_url
  if (!sessionId || !wsUrl) {
    throw new Error('Invalid replay session response')
  }
  return { sessionId, wsUrl }
}

export function normalizeReplayState(raw: RawStateResponse): ReplayStateResponse {
  const sessionId = raw.sessionId ?? raw.session_id
  if (!sessionId || !raw.symbol || !raw.timeframe || raw.state == null || raw.speed == null) {
    throw new Error('Invalid replay state response')
  }
  return {
    sessionId,
    symbol: raw.symbol,
    timeframe: raw.timeframe,
    stepTimeframe: raw.stepTimeframe ?? raw.step_timeframe ?? raw.timeframe,
    startAnchor: raw.startAnchor ?? raw.start ?? 0,
    latestAvailable: raw.latestAvailable ?? raw.latest_available ?? null,
    cursor: raw.cursor ?? null,
    state: raw.state,
    speed: raw.speed,
    barIndex: raw.barIndex ?? raw.bar_index ?? 0,
    queueRemaining: raw.queueRemaining ?? raw.queue_remaining ?? 0,
    indicators: raw.indicators ?? [],
  }
}

export function createReplaySession(
  body: ReplaySessionCreateRequest,
): Promise<ReplaySessionCreateResponse> {
  return apiRequest<RawSessionCreateResponse>('/replay/sessions', {
    method: 'POST',
    body: JSON.stringify({
      symbol: body.symbol,
      timeframe: body.timeframe,
      start: body.start,
      indicators: body.indicators,
      step_timeframe: body.step_timeframe ?? null,
      speed: body.speed ?? 1,
    }),
  }).then(normalizeCreateResponse)
}

export function getReplaySession(sessionId: string): Promise<ReplayStateResponse> {
  return apiRequest<RawStateResponse>(`/replay/sessions/${sessionId}`).then(normalizeReplayState)
}

export function deleteReplaySession(sessionId: string): Promise<void> {
  return apiRequest<void>(`/replay/sessions/${sessionId}`, { method: 'DELETE' })
}

/**
 * Build a browser WebSocket URL from the server path (e.g. `/ws/replay/{id}`).
 */
export function buildReplayWsUrl(wsPath: string): string {
  if (wsPath.startsWith('ws://') || wsPath.startsWith('wss://')) {
    return wsPath
  }

  const apiBase = import.meta.env.VITE_API_BASE ?? '/api/v1'
  if (typeof apiBase === 'string' && apiBase.startsWith('http')) {
    const url = new URL(apiBase)
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${url.host}${wsPath}`
  }

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${wsProtocol}//${window.location.host}${wsPath}`
}
