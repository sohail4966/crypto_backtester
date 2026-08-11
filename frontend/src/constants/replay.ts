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

export const REPLAY_CLOSE_SUPERSEDED = 4401
export const REPLAY_CLOSE_NOT_FOUND = 4404
