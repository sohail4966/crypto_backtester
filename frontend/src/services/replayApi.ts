import { apiRequest, ApiError } from '@/services/api'
import { USER_ID_STORAGE_KEY } from '@/constants/watchlist'
import type {
  ReplayCreateBody,
  ReplayCreateResponse,
  ReplaySessionMeta,
} from '@/types/replay'
import {
  normalizeCreateResponse,
  normalizeSessionMeta,
} from '@/utils/replayNormalize'

export async function createReplaySession(
  body: ReplayCreateBody,
): Promise<ReplayCreateResponse> {
  const wire = {
    symbol: body.symbol,
    timeframe: body.timeframe,
    start: body.start,
    indicators: body.indicators,
    speed: body.speed,
    autoplay: body.autoplay,
    user_id: localStorage.getItem(USER_ID_STORAGE_KEY) ?? undefined,
  }
  const raw = await apiRequest<unknown>('/replay/sessions', {
    method: 'POST',
    body: JSON.stringify(wire),
  })
  return normalizeCreateResponse(raw)
}

export async function getReplaySession(
  sessionId: string,
): Promise<ReplaySessionMeta> {
  const raw = await apiRequest<unknown>(
    `/replay/sessions/${encodeURIComponent(sessionId)}`,
  )
  return normalizeSessionMeta(raw, sessionId)
}

/** Best-effort teardown; 404 treated as success. */
export async function deleteReplaySession(sessionId: string): Promise<void> {
  try {
    await apiRequest<void>(
      `/replay/sessions/${encodeURIComponent(sessionId)}`,
      { method: 'DELETE' },
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return
    }
    throw error
  }
}
