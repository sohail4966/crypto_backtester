import type { ReplayServerEvent, ReplayWsCommand } from '@/types/replay'
import { logReplayWsLifecycle, logReplayWsRecv, logReplayWsSend } from '@/utils/replayWsLog'
import { parseReplayWsMessage } from '@/utils/replayWsParse'

export type ReplayWsListener = (event: ReplayServerEvent) => void
export type ReplayWsCloseListener = (code: number, reason: string) => void
export type ReplayWsOpenListener = () => void

export interface ReplayWsClient {
  connect: () => void
  disconnect: () => void
  send: (command: ReplayWsCommand) => void
  onEvent: (listener: ReplayWsListener) => () => void
  onClose: (listener: ReplayWsCloseListener) => () => void
  onOpen: (listener: ReplayWsOpenListener) => () => void
  isOpen: () => boolean
}

export function createReplayWsClient(url: string): ReplayWsClient {
  let socket: WebSocket | null = null
  const eventListeners = new Set<ReplayWsListener>()
  const closeListeners = new Set<ReplayWsCloseListener>()
  const openListeners = new Set<ReplayWsOpenListener>()
  const pendingCommands: ReplayWsCommand[] = []

  const notifyEvent = (event: ReplayServerEvent) => {
    logReplayWsRecv(event)
    eventListeners.forEach((listener) => listener(event))
  }

  const notifyClose = (code: number, reason: string) => {
    logReplayWsLifecycle(`closed code=${code}`, reason || '(no reason)')
    closeListeners.forEach((listener) => listener(code, reason))
  }

  const notifyOpen = () => {
    logReplayWsLifecycle('open')
    openListeners.forEach((listener) => listener())
  }

  const flushPending = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return
    }
    while (pendingCommands.length > 0) {
      const command = pendingCommands.shift()
      if (command) {
        socket.send(JSON.stringify(command))
        logReplayWsSend(command, false)
      }
    }
  }

  return {
    connect() {
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return
      }
      pendingCommands.length = 0
      logReplayWsLifecycle('connecting', url)
      socket = new WebSocket(url)

      socket.addEventListener('open', () => {
        notifyOpen()
        flushPending()
      })

      socket.addEventListener('message', async (message) => {
        try {
          const raw =
            typeof message.data === 'string'
              ? message.data
              : await (message.data as Blob).text()
          const payload = parseReplayWsMessage(raw) as ReplayServerEvent
          if (payload && typeof payload === 'object' && 'type' in payload) {
            notifyEvent(payload)
          } else {
            logReplayWsLifecycle('ignored non-event frame', payload)
          }
        } catch (error) {
          const preview =
            typeof message.data === 'string'
              ? message.data.slice(0, 240)
              : '(binary frame)'
          logReplayWsLifecycle('failed to parse frame', { error, preview })
        }
      })

      socket.addEventListener('error', (error) => {
        logReplayWsLifecycle('socket error', error)
      })

      socket.addEventListener('close', (event) => {
        notifyClose(event.code, event.reason)
        socket = null
        pendingCommands.length = 0
      })
    },

    disconnect() {
      if (!socket) {
        pendingCommands.length = 0
        return
      }
      logReplayWsLifecycle('disconnect')
      socket.close(1000, 'client_disconnect')
      socket = null
      pendingCommands.length = 0
    },

    send(command: ReplayWsCommand) {
      if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        logReplayWsLifecycle('send dropped — socket closed', command)
        return
      }
      if (socket.readyState === WebSocket.CONNECTING) {
        pendingCommands.push(command)
        logReplayWsSend(command, true)
        return
      }
      if (socket.readyState !== WebSocket.OPEN) {
        logReplayWsLifecycle('send dropped — socket not open', command)
        return
      }
      socket.send(JSON.stringify(command))
      logReplayWsSend(command, false)
    },

    onEvent(listener: ReplayWsListener) {
      eventListeners.add(listener)
      return () => eventListeners.delete(listener)
    },

    onClose(listener: ReplayWsCloseListener) {
      closeListeners.add(listener)
      return () => closeListeners.delete(listener)
    },

    onOpen(listener: ReplayWsOpenListener) {
      openListeners.add(listener)
      return () => openListeners.delete(listener)
    },

    isOpen() {
      return socket?.readyState === WebSocket.OPEN
    },
  }
}
