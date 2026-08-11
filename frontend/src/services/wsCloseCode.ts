/**
 * Shared WebSocket close-code helper (FE-L2-002 / FE-L2-007).
 *
 * Backend contract (unchanged):
 *   4401 = UNAUTHORIZED (JWT missing/invalid/expired)
 *   4402 = SUPERSEDED (another connection took over)
 *   4404 = REPLAY_NOT_FOUND
 *   4429 = WS_LIMIT (per-user concurrent-connection cap)
 *   1000 / 1001 = normal close / going-away
 */

export const WS_CLOSE_UNAUTHORIZED = 4401
export const WS_CLOSE_SUPERSEDED = 4402
export const WS_CLOSE_NOT_FOUND = 4404
export const WS_CLOSE_RATE_LIMITED = 4429

export type WsCloseKind =
  | 'unauthorized'
  | 'superseded'
  | 'not_found'
  | 'rate_limited'
  | 'closed'
  | 'error'

export function classifyWsCloseKind(code: number): WsCloseKind {
  if (code === WS_CLOSE_UNAUTHORIZED) {
    return 'unauthorized'
  }
  if (code === WS_CLOSE_SUPERSEDED) {
    return 'superseded'
  }
  if (code === WS_CLOSE_NOT_FOUND) {
    return 'not_found'
  }
  if (code === WS_CLOSE_RATE_LIMITED) {
    return 'rate_limited'
  }
  if (code === 1000 || code === 1001) {
    return 'closed'
  }
  return 'error'
}
