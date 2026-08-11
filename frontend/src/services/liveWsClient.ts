import { getWsConnectUrl } from '@/services/wsTicketClient'
import { classifyWsCloseKind, type WsCloseKind } from '@/services/wsCloseCode'
import type { OHLCVBar } from '@/types/candle'

export type LiveWsHandlers = {
  onCandle?: (payload: {
    symbol: string
    timeframe: string
    bar: OHLCVBar
  }) => void
  onOpen?: () => void
  onClose?: (info: { code: number; reason: string; kind: WsCloseKind }) => void
  onError?: (error: Event) => void
}

export function resolveLiveWsBase(location = window.location): string {
  const configured = import.meta.env.VITE_LIVE_WS_URL as string | undefined
  if (configured) {
    if (configured.startsWith('ws://') || configured.startsWith('wss://')) {
      const parsed = new URL(configured)
      if (parsed.host !== location.host) {
        throw new Error(
          `Refusing to open live WS on foreign host: ${parsed.host}`,
        )
      }
      return configured
    }
    const path = configured.startsWith('/') ? configured : `/${configured}`
    return `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${path}`
  }
  return `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/live`
}

/**
 * Live candle WebSocket client (FE-005). Feature-gated by VITE_LIVE_WS.
 * Mirrors ReplayWsClient patterns. Auth via short-lived ?ticket= (or legacy ?token=).
 */
export class LiveWsClient {
  private socket: WebSocket | null = null
  private handlers: LiveWsHandlers = {}
  private subscriptions = new Map<string, { symbol: string; timeframe: string }>()

  async connect(handlers: LiveWsHandlers = {}): Promise<void> {
    this.close()
    this.handlers = handlers
    const base = resolveLiveWsBase()
    const url = await getWsConnectUrl(base)
    const socket = new WebSocket(url)
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
        const barRaw = row.bar
        if (!barRaw || typeof barRaw !== 'object') {
          return
        }
        const b = barRaw as Record<string, unknown>
        const bar: OHLCVBar = {
          time: Number(b.time),
          open: Number(b.open),
          high: Number(b.high),
          low: Number(b.low),
          close: Number(b.close),
          volume: Number(b.volume ?? 0),
        }
        this.handlers.onCandle?.({
          symbol: String(row.symbol ?? ''),
          timeframe: String(row.timeframe ?? ''),
          bar,
        })
      } catch {
        // ignore malformed
      }
    }

    socket.onerror = (error) => this.handlers.onError?.(error)
    socket.onclose = (event) => {
      if (this.socket === socket) {
        this.socket = null
      }
      this.handlers.onClose?.({
        code: event.code,
        reason: event.reason,
        kind: classifyWsCloseKind(event.code),
      })
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
