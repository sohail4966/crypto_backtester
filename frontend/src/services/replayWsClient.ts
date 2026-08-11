import {
  REPLAY_CLOSE_NOT_FOUND,
  REPLAY_CLOSE_SUPERSEDED,
  REPLAY_CLOSE_UNAUTHORIZED,
} from '@/constants/replay'
import { getAuthToken } from '@/services/authToken'
import type { ReplayWsInbound, ReplayWsOutbound } from '@/types/replay'
import { normalizeWsInbound } from '@/utils/replayNormalize'

export type ReplayWsCloseReason =
  | 'unauthorized'
  | 'superseded'
  | 'not_found'
  | 'closed'
  | 'error'

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

const MAX_QUEUE = 32

export function resolveReplayWsUrl(wsUrl: string, location = window.location): string {
  if (wsUrl.startsWith('ws://') || wsUrl.startsWith('wss://')) {
    return appendToken(wsUrl)
  }
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const path = wsUrl.startsWith('/') ? wsUrl : `/${wsUrl}`
  return appendToken(`${protocol}//${location.host}${path}`)
}

function appendToken(url: string): string {
  const token = getAuthToken()
  if (!token) {
    return url
  }
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}token=${encodeURIComponent(token)}`
}

function closeKind(code: number): ReplayWsCloseReason {
  if (code === REPLAY_CLOSE_UNAUTHORIZED) {
    return 'unauthorized'
  }
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

function coalesceQueue(
  queue: ReplayWsOutbound[],
  cmd: ReplayWsOutbound,
): ReplayWsOutbound[] {
  const next = [...queue]
  if (cmd.action === 'set_speed') {
    const idx = next.findIndex((item) => item.action === 'set_speed')
    if (idx >= 0) {
      next[idx] = cmd
      return next
    }
  }
  if (cmd.action === 'seek') {
    const idx = next.findIndex((item) => item.action === 'seek')
    if (idx >= 0) {
      next[idx] = cmd
      return next
    }
  }
  if (cmd.action === 'play' || cmd.action === 'pause') {
    // Latest transport intent wins — drop prior play/pause.
    const filtered = next.filter(
      (item): item is Exclude<ReplayWsOutbound, { action: 'play' } | { action: 'pause' }> =>
        item.action !== 'play' && item.action !== 'pause',
    )
    return [...filtered, cmd]
  }
  if (next.length >= MAX_QUEUE) {
    next.shift()
  }
  next.push(cmd)
  return next
}

export class ReplayWsClient {
  private socket: WebSocket | null = null
  private handlers: ReplayWsHandlers = {}
  private outboundQueue: ReplayWsOutbound[] = []
  private pendingPlay = false

  connect(wsUrl: string, handlers: ReplayWsHandlers = {}): void {
    this.close({ clearQueue: false })
    this.handlers = handlers
    const url = resolveReplayWsUrl(wsUrl)
    const socket = new WebSocket(url)
    this.socket = socket

    socket.onopen = () => {
      this.flushQueue()
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
    if (cmd.action === 'play') {
      this.pendingPlay = true
    } else if (cmd.action === 'pause') {
      this.pendingPlay = false
    }

    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(cmd))
      return
    }
    this.outboundQueue = coalesceQueue(this.outboundQueue, cmd)
  }

  /** True if a play was queued/sent and not cancelled by pause; cleared when read. */
  consumePendingPlay(): boolean {
    const value = this.pendingPlay
    this.pendingPlay = false
    return value
  }

  clearQueue(): void {
    this.outboundQueue = []
    this.pendingPlay = false
  }

  get queuedCount(): number {
    return this.outboundQueue.length
  }

  private flushQueue(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return
    }
    const pending = this.outboundQueue
    this.outboundQueue = []
    for (const cmd of pending) {
      this.socket.send(JSON.stringify(cmd))
    }
  }

  close(options: { clearQueue?: boolean } = {}): void {
    const { clearQueue = true } = options
    if (clearQueue) {
      this.outboundQueue = []
      this.pendingPlay = false
    }
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
