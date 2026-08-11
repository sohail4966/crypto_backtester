import { getAuthToken } from '@/services/authToken'
import type { OHLCVBar } from '@/types/candle'

export type LiveWsHandlers = {
  onCandle?: (payload: {
    symbol: string
    timeframe: string
    candle: OHLCVBar
    incomplete?: boolean
  }) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
}

function resolveLiveWsUrl(location = window.location): string {
  const configured = import.meta.env.VITE_LIVE_WS_URL as string | undefined
  const base =
    configured ??
    `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/live`
  const token = getAuthToken()
  if (!token) {
    return base
  }
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}token=${encodeURIComponent(token)}`
}

/**
 * Live candle WebSocket client (FE-005). Feature-gated by VITE_LIVE_WS.
 * Mirrors ReplayWsClient patterns; auth via ?token= (BE-004/006 style).
 */
export class LiveWsClient {
  private socket: WebSocket | null = null
  private handlers: LiveWsHandlers = {}
  private subscriptions = new Map<string, { symbol: string; timeframe: string }>()

  connect(handlers: LiveWsHandlers = {}): void {
    this.close()
    this.handlers = handlers
    const socket = new WebSocket(resolveLiveWsUrl())
    this.socket = socket

    socket.onopen = () => {
      for (const sub of this.subscriptions.values()) {
        this.sendSubscribe(sub.symbol, sub.timeframe)
      }
      this.handlers.onOpen?.()
    }

    socket.onmessage = (event) => {
      try {
        const parsed: unknown = JSON.parse(String(event.data))
        if (!parsed || typeof parsed !== 'object') {
          return
        }
        const row = parsed as Record<string, unknown>
        if (row.type !== 'candle') {
          return
        }
        const candleRaw = row.candle
        if (!candleRaw || typeof candleRaw !== 'object') {
          return
        }
        const c = candleRaw as Record<string, unknown>
        const candle: OHLCVBar = {
          time: Number(c.time ?? c.t),
          open: Number(c.open ?? c.o),
          high: Number(c.high ?? c.h),
          low: Number(c.low ?? c.l),
          close: Number(c.close ?? c.c),
          volume: Number(c.volume ?? c.v ?? 0),
        }
        this.handlers.onCandle?.({
          symbol: String(row.symbol ?? ''),
          timeframe: String(row.timeframe ?? ''),
          candle,
          incomplete: Boolean(row.incomplete),
        })
      } catch {
        // ignore malformed
      }
    }

    socket.onerror = (error) => this.handlers.onError?.(error)
    socket.onclose = () => {
      if (this.socket === socket) {
        this.socket = null
      }
      this.handlers.onClose?.()
    }
  }

  subscribe(symbol: string, timeframe: string): void {
    const key = `${symbol}:${timeframe}`
    this.subscriptions.set(key, { symbol, timeframe })
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.sendSubscribe(symbol, timeframe)
    }
  }

  unsubscribe(symbol: string, timeframe: string): void {
    const key = `${symbol}:${timeframe}`
    this.subscriptions.delete(key)
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({ action: 'unsubscribe', symbols: [symbol], timeframe }),
      )
    }
  }

  private sendSubscribe(symbol: string, timeframe: string): void {
    this.socket?.send(
      JSON.stringify({ action: 'subscribe', symbols: [symbol], timeframe }),
    )
  }

  close(): void {
    const socket = this.socket
    this.socket = null
    if (!socket) {
      return
    }
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null
    if (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    ) {
      socket.close(1000, 'client_close')
    }
  }
}

export function isLiveWsEnabled(): boolean {
  const flag = import.meta.env.VITE_LIVE_WS
  return flag === 'true' || flag === '1'
}
