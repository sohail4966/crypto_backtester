import {
  REPLAY_CLOSE_NOT_FOUND,
  REPLAY_CLOSE_SUPERSEDED,
} from '@/constants/replay'
import type { ReplayWsInbound, ReplayWsOutbound } from '@/types/replay'
import { normalizeWsInbound } from '@/utils/replayNormalize'

export type ReplayWsCloseReason = 'superseded' | 'not_found' | 'closed' | 'error'

export interface ReplayWsHandlers {
  onEvent?: (event: ReplayWsInbound) => void
  onOpen?: () => void
  onClose?: (info: {
    code: number
    reason: string
    kind: ReplayWsCloseReason
  }) => void
  onError?: (error: Event) => void
}

export function resolveReplayWsUrl(wsUrl: string, location = window.location): string {
  if (wsUrl.startsWith('ws://') || wsUrl.startsWith('wss://')) {
    return wsUrl
  }
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const path = wsUrl.startsWith('/') ? wsUrl : `/${wsUrl}`
  return `${protocol}//${location.host}${path}`
}

function closeKind(code: number): ReplayWsCloseReason {
  if (code === REPLAY_CLOSE_SUPERSEDED) {
    return 'superseded'
  }
  if (code === REPLAY_CLOSE_NOT_FOUND) {
    return 'not_found'
  }
  if (code === 1000 || code === 1001) {
    return 'closed'
  }
  return 'error'
}

export class ReplayWsClient {
  private socket: WebSocket | null = null
  private handlers: ReplayWsHandlers = {}

  connect(wsUrl: string, handlers: ReplayWsHandlers = {}): void {
    this.close()
    this.handlers = handlers
    const url = resolveReplayWsUrl(wsUrl)
    const socket = new WebSocket(url)
    this.socket = socket

    socket.onopen = () => {
      this.handlers.onOpen?.()
    }

    socket.onmessage = (event) => {
      try {
        const parsed: unknown = JSON.parse(String(event.data))
        const normalized = normalizeWsInbound(parsed)
        if (normalized) {
          this.handlers.onEvent?.(normalized)
        }
      } catch {
        // Ignore malformed frames
      }
    }

    socket.onerror = (error) => {
      this.handlers.onError?.(error)
    }

    socket.onclose = (event) => {
      const kind = closeKind(event.code)
      this.handlers.onClose?.({
        code: event.code,
        reason: event.reason,
        kind,
      })
      if (this.socket === socket) {
        this.socket = null
      }
    }
  }

  send(cmd: ReplayWsOutbound): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return
    }
    this.socket.send(JSON.stringify(cmd))
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

  get readyState(): number {
    return this.socket?.readyState ?? WebSocket.CLOSED
  }
}
