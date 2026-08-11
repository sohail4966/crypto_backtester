/**
 * WebSocket ticket client (FE-L2-003).
 *
 * Trades the in-memory JWT for a single-use, short-lived opaque ticket that is
 * appended to the WS URL as ``?ticket=<value>``. This keeps the raw JWT out of
 * URLs (DevTools, HAR exports, referrer headers, browser history).
 *
 * Tickets are one-shot on the BE side — we do not cache them across connects.
 * Legacy ``?token=<jwt>`` remains supported when the ticket flag is disabled
 * so the FE can be rolled out incrementally.
 */

import { apiRequest } from '@/services/api'
import { getAuthToken } from '@/services/authToken'

interface WsTicketResponse {
  ticket: string
  expires_in: number
}

/**
 * Feature flag — when enabled the FE authenticates WS handshakes via a
 * one-shot ticket instead of appending the JWT as ``?token=``.
 *
 * Defaults:
 *   - production: ON (unless VITE_WS_TICKET=false is set explicitly)
 *   - dev / test: OFF (unless VITE_WS_TICKET=true is set explicitly)
 */
export function isWsTicketAuthEnabled(): boolean {
  const flag = import.meta.env.VITE_WS_TICKET
  if (flag === 'true' || flag === '1') {
    return true
  }
  if (flag === 'false' || flag === '0') {
    return false
  }
  return !import.meta.env.DEV
}

/**
 * POST /ws/tickets → returns an opaque, single-use ticket.
 *
 * Returns ``null`` when no JWT is present (unauthenticated WS attempt) so
 * callers can decide how to handle it (mirrors the legacy no-op behaviour of
 * the ``?token=`` path).
 */
export async function getWsTicket(): Promise<string | null> {
  const token = getAuthToken()
  if (!token) {
    return null
  }
  const resp = await apiRequest<WsTicketResponse>('/ws/tickets', {
    method: 'POST',
  })
  return resp.ticket
}

/** Test-only helper — no state today, but kept for symmetry with future caching. */
export function resetWsTicketCache(): void {
  // Intentionally empty: tickets are single-use, not cached.
}

/**
 * Build the final WS URL used by ``new WebSocket(...)``. When ticket auth is
 * enabled we mint a fresh ticket, otherwise we fall back to appending the
 * legacy ``?token=<jwt>`` query param.
 */
export async function getWsConnectUrl(baseUrl: string): Promise<string> {
  if (isWsTicketAuthEnabled()) {
    const ticket = await getWsTicket()
    if (!ticket) {
      return baseUrl
    }
    const sep = baseUrl.includes('?') ? '&' : '?'
    return `${baseUrl}${sep}ticket=${encodeURIComponent(ticket)}`
  }
  const token = getAuthToken()
  if (!token) {
    return baseUrl
  }
  const sep = baseUrl.includes('?') ? '&' : '?'
  return `${baseUrl}${sep}token=${encodeURIComponent(token)}`
}
