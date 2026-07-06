import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { createReplayWsClient } from '@/services/replayWsClient'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CONNECTING = 0
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  sent: string[] = []
  url: string
  private listeners = new Map<string, Set<(...args: unknown[]) => void>>()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: (...args: unknown[]) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type)!.add(listener)
  }

  removeEventListener(type: string, listener: (...args: unknown[]) => void) {
    this.listeners.get(type)?.delete(listener)
  }

  private emit(type: string, ...args: unknown[]) {
    this.listeners.get(type)?.forEach((listener) => listener(...args))
  }

  send(data: string) {
    this.sent.push(data)
  }

  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED
    this.emit('close', { code, reason })
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN
    this.emit('open')
  }
}

describe('createReplayWsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('queues commands sent while connecting and flushes on open', () => {
    const client = createReplayWsClient('ws://test/ws/replay/id')
    const openHandler = vi.fn()
    client.onOpen(openHandler)
    client.connect()
    client.send({ action: 'play', speed: 1 })

    const socket = MockWebSocket.instances[0]
    expect(socket.sent).toHaveLength(0)

    socket.simulateOpen()
    expect(openHandler).toHaveBeenCalled()
    expect(socket.sent).toHaveLength(1)
    expect(JSON.parse(socket.sent[0])).toEqual({ action: 'play', speed: 1 })
  })
})
