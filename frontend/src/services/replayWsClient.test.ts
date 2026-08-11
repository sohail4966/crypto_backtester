import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ReplayWsClient,
  resolveReplayWsUrl,
} from '@/services/replayWsClient'

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static CLOSING = 2
  static CLOSED = 3
  static instances: MockWebSocket[] = []

  readyState = MockWebSocket.CONNECTING
  url: string
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  sent: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code, reason } as CloseEvent)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }
}

describe('replayWsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    localStorage.clear()
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('builds ws URL from relative path', () => {
    expect(
      resolveReplayWsUrl('/ws/replay/abc', {
        protocol: 'http:',
        host: 'localhost:5173',
      } as Location),
    ).toBe('ws://localhost:5173/ws/replay/abc')
  })

  it('dispatches typed events and serializes send', () => {
    const client = new ReplayWsClient()
    const onEvent = vi.fn()
    client.connect('/ws/replay/x', { onEvent })
    const socket = MockWebSocket.instances[0]!
    socket.open()
    socket.emit({
      type: 'buffer_loading',
    })
    expect(onEvent).toHaveBeenCalledWith({ type: 'buffer_loading' })

    client.send({ action: 'step', count: 1 })
    expect(JSON.parse(socket.sent[0]!)).toEqual({ action: 'step', count: 1 })
  })

  it('maps distinct close codes for auth, superseded, and not_found', () => {
    const client = new ReplayWsClient()
    const onClose = vi.fn()
    client.connect('/ws/replay/x', { onClose })
    const socket = MockWebSocket.instances[0]!
    socket.open()
    socket.close(4401, 'UNAUTHORIZED')
    expect(onClose).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4401, kind: 'unauthorized' }),
    )

    const client2 = new ReplayWsClient()
    const onClose2 = vi.fn()
    client2.connect('/ws/replay/y', { onClose: onClose2 })
    MockWebSocket.instances[1]!.close(4402, 'SUPERSEDED')
    expect(onClose2).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4402, kind: 'superseded' }),
    )

    const client3 = new ReplayWsClient()
    const onClose3 = vi.fn()
    client3.connect('/ws/replay/z', { onClose: onClose3 })
    MockWebSocket.instances[2]!.close(4404, 'missing')
    expect(onClose3).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4404, kind: 'not_found' }),
    )
  })

  it('queues commands until socket opens then flushes', () => {
    const client = new ReplayWsClient()
    client.connect('/ws/replay/x')
    const socket = MockWebSocket.instances[0]!
    client.send({ action: 'play', speed: 1 })
    expect(socket.sent).toHaveLength(0)
    expect(client.queuedCount).toBe(1)
    socket.open()
    expect(JSON.parse(socket.sent[0]!)).toEqual({ action: 'play', speed: 1 })
    expect(client.consumePendingPlay()).toBe(true)
  })

  it('appends token query when auth token present', () => {
    localStorage.setItem('auth_token', 'abc')
    expect(
      resolveReplayWsUrl('/ws/replay/abc', {
        protocol: 'http:',
        host: 'localhost:5173',
      } as Location),
    ).toBe('ws://localhost:5173/ws/replay/abc?token=abc')
  })
})
