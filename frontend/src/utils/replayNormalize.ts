import type { OHLCVBar } from '@/types/candle'
import type { IndicatorPoint, IndicatorSeriesMap, IndicatorSpec } from '@/types/indicator'
import type {
  ReplayCreateResponse,
  ReplayServerState,
  ReplaySessionMeta,
  ReplaySnapshot,
  ReplayTick,
  ReplayWsInbound,
} from '@/types/replay'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function pickString(obj: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = obj[key]
    if (typeof value === 'string') {
      return value
    }
  }
  return undefined
}

function pickNumber(obj: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const key of keys) {
    const value = obj[key]
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value
    }
  }
  return undefined
}

function pickNullableNumber(
  obj: Record<string, unknown>,
  ...keys: string[]
): number | null | undefined {
  for (const key of keys) {
    const value = obj[key]
    if (value === null) {
      return null
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value
    }
  }
  return undefined
}

function normalizeBar(raw: unknown): OHLCVBar | null {
  if (!isRecord(raw)) {
    return null
  }
  const time = pickNumber(raw, 'time')
  const open = pickNumber(raw, 'open')
  const high = pickNumber(raw, 'high')
  const low = pickNumber(raw, 'low')
  const close = pickNumber(raw, 'close')
  const volume = pickNumber(raw, 'volume') ?? 0
  if (
    time == null ||
    open == null ||
    high == null ||
    low == null ||
    close == null
  ) {
    return null
  }
  return { time, open, high, low, close, volume }
}

function normalizeIndicatorPoint(raw: unknown): IndicatorPoint | null {
  if (!isRecord(raw)) {
    return null
  }
  const time = pickNumber(raw, 'time')
  if (time == null) {
    return null
  }
  const value = raw.value
  if (value === null) {
    return { time, value: null }
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return { time, value }
  }
  return null
}

function normalizeIndicatorSeriesMap(raw: unknown): IndicatorSeriesMap {
  if (!isRecord(raw)) {
    return {}
  }
  const out: IndicatorSeriesMap = {}
  for (const [key, value] of Object.entries(raw)) {
    if (!Array.isArray(value)) {
      continue
    }
    out[key] = value
      .map(normalizeIndicatorPoint)
      .filter((point): point is IndicatorPoint => point != null)
  }
  return out
}

function normalizeTickIndicators(
  raw: unknown,
): Record<string, IndicatorPoint> {
  if (!isRecord(raw)) {
    return {}
  }
  const out: Record<string, IndicatorPoint> = {}
  for (const [key, value] of Object.entries(raw)) {
    const point = normalizeIndicatorPoint(value)
    if (point) {
      out[key] = point
    }
  }
  return out
}

function normalizeIndicatorSpecs(raw: unknown): IndicatorSpec[] {
  if (!Array.isArray(raw)) {
    return []
  }
  const specs: IndicatorSpec[] = []
  for (const item of raw) {
    if (!isRecord(item) || typeof item.key !== 'string') {
      continue
    }
    const params =
      isRecord(item.params) ? (item.params as Record<string, unknown>) : {}
    const pane =
      item.pane === 'overlay' || item.pane === 'subchart' ? item.pane : undefined
    specs.push({ key: item.key, params, pane })
  }
  return specs
}

function normalizeServerState(value: unknown): ReplayServerState {
  if (
    value === 'idle' ||
    value === 'playing' ||
    value === 'paused' ||
    value === 'completed'
  ) {
    return value
  }
  return 'paused'
}

export function normalizeCreateResponse(raw: unknown): ReplayCreateResponse {
  if (!isRecord(raw)) {
    throw new Error('Invalid replay create response')
  }
  const sessionId = pickString(raw, 'sessionId', 'session_id')
  const wsUrl = pickString(raw, 'wsUrl', 'ws_url')
  if (!sessionId || !wsUrl) {
    throw new Error('Invalid replay create response: missing sessionId/wsUrl')
  }
  return { sessionId, wsUrl }
}

export function normalizeSessionMeta(
  raw: unknown,
  fallbackSessionId?: string,
): ReplaySessionMeta {
  if (!isRecord(raw)) {
    throw new Error('Invalid replay session state')
  }

  const sessionId =
    pickString(raw, 'sessionId', 'session_id') ?? fallbackSessionId
  if (!sessionId) {
    throw new Error('Invalid replay session state: missing sessionId')
  }

  const startAnchor =
    pickNumber(raw, 'startAnchor', 'start_anchor', 'start') ?? 0
  const latestAvailable =
    pickNullableNumber(raw, 'latestAvailable', 'latest_available') ?? null
  const cursor = pickNullableNumber(raw, 'cursor', 'cursor_ts') ?? null

  return {
    sessionId,
    symbol: pickString(raw, 'symbol') ?? '',
    timeframe: pickString(raw, 'timeframe') ?? '',
    stepTimeframe:
      pickString(raw, 'stepTimeframe', 'step_timeframe') ??
      pickString(raw, 'timeframe') ??
      '',
    startAnchor,
    latestAvailable,
    cursor,
    serverState: normalizeServerState(raw.state ?? raw.serverState),
    speed: pickNumber(raw, 'speed') ?? 1,
    barIndex: pickNumber(raw, 'barIndex', 'bar_index') ?? 0,
    queueRemaining: pickNumber(raw, 'queueRemaining', 'queue_remaining') ?? 0,
    indicators: normalizeIndicatorSpecs(raw.indicators),
  }
}

export function normalizeSnapshot(raw: unknown): ReplaySnapshot {
  if (!isRecord(raw)) {
    throw new Error('Invalid replay snapshot')
  }
  const bars = Array.isArray(raw.bars)
    ? raw.bars.map(normalizeBar).filter((bar): bar is OHLCVBar => bar != null)
    : []
  return {
    bars,
    indicators: normalizeIndicatorSeriesMap(raw.indicators),
    cursor: pickNullableNumber(raw, 'cursor') ?? null,
    startAnchor: pickNumber(raw, 'startAnchor', 'start_anchor') ?? 0,
    latestAvailable:
      pickNullableNumber(raw, 'latestAvailable', 'latest_available') ?? null,
  }
}

function normalizeTick(raw: unknown): ReplayTick | null {
  if (!isRecord(raw)) {
    return null
  }
  const bar = normalizeBar(raw.bar)
  if (!bar) {
    return null
  }
  return {
    bar,
    indicators: normalizeTickIndicators(raw.indicators),
  }
}

export function normalizeWsInbound(raw: unknown): ReplayWsInbound | null {
  if (!isRecord(raw) || typeof raw.type !== 'string') {
    return null
  }

  switch (raw.type) {
    case 'replay_state':
      return { type: 'replay_state', ...normalizeSessionMeta(raw) }
    case 'snapshot':
      return { type: 'snapshot', ...normalizeSnapshot(raw) }
    case 'tick_batch': {
      const ticks = Array.isArray(raw.ticks)
        ? raw.ticks.map(normalizeTick).filter((t): t is ReplayTick => t != null)
        : []
      return {
        type: 'tick_batch',
        ticks,
        cursor: pickNullableNumber(raw, 'cursor') ?? null,
        queueRemaining:
          pickNumber(raw, 'queueRemaining', 'queue_remaining') ?? 0,
      }
    }
    case 'buffer_loading':
      return { type: 'buffer_loading' }
    case 'buffer_ready':
      return {
        type: 'buffer_ready',
        bufferEnd: pickNullableNumber(raw, 'bufferEnd', 'buffer_end') ?? null,
        latestAvailable:
          pickNullableNumber(raw, 'latestAvailable', 'latest_available') ?? null,
      }
    case 'buffer_reset':
      return { type: 'buffer_reset' }
    case 'replay_completed':
      return { type: 'replay_completed' }
    case 'error':
      return {
        type: 'error',
        code: pickString(raw, 'code') ?? 'ERROR',
        message: pickString(raw, 'message') ?? 'Replay error',
      }
    default:
      return null
  }
}
