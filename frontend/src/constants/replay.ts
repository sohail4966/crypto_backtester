import type { ReplaySpeed } from '@/types/replay'

export const REPLAY_SPEEDS: ReplaySpeed[] = [0.5, 1, 2, 5, 10]
export const REPLAY_REFILL_THRESHOLD = 20
export const REPLAY_BASE_INTERVAL_MS = 1000
export const REPLAY_MIN_INTERVAL_MS = 50
export const REPLAY_BUFFER_UI_TIMEOUT_MS = 3000
export const REPLAY_SESSION_QUERY = 'replaySession'

export function replayIntervalMs(speed: number): number {
  return Math.max(REPLAY_MIN_INTERVAL_MS, REPLAY_BASE_INTERVAL_MS / speed)
}

/** Auth failure on replay WS (BE: WS_UNAUTHORIZED). */
export const REPLAY_CLOSE_UNAUTHORIZED = 4401
/** Another tab/connection took over this session. */
export const REPLAY_CLOSE_SUPERSEDED = 4402
export const REPLAY_CLOSE_NOT_FOUND = 4404
/** Per-user concurrent WebSocket connection cap (BE: WS_LIMIT). */
export const REPLAY_CLOSE_LIMIT = 4429
