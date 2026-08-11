import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ReplayWsClient,
  resolveReplayWsBase,
  resolveReplayWsUrl,
} from '@/services/replayWsClient'
import {
  clearAuthToken,
  resetAuthTokenForTests,
  setAuthToken,
} from '@/services/authToken'

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

/**
 * Wait for the async ``connect(...)`` to finish resolving the URL and construct
 * the underlying MockWebSocket. Waits until ``instances.length`` grows beyond
 * ``sinceCount`` so callers can request only the newly-created socket.
 */
async function waitForSocket(sinceCount = 0): Promise<MockWebSocket> {
  for (let i = 0; i < 40; i += 1) {
    if (MockWebSocket.instances.length > sinceCount) {
      return MockWebSocket.instances[MockWebSocket.instances.length - 1]!
    }
    await Promise.resolve()
  }
  throw new Error('MockWebSocket was never constructed')
}

describe('replayWsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    localStorage.clear()
    resetAuthTokenForTests()
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearAuthToken()
  })

  it('builds ws URL base from relative path (sync)', () => {
    expect(
      resolveReplayWsBase('/ws/replay/abc', {
        protocol: 'http:',
        host: 'localhost:5173',
      } as Location),
    ).toBe('ws://localhost:5173/ws/replay/abc')
  })

  it('resolveReplayWsUrl (async) attaches ?token= when a JWT is set', async () => {
    setAuthToken('abc')
    const url = await resolveReplayWsUrl('/ws/replay/abc', {
      protocol: 'http:',
      host: 'localhost:5173',
    } as Location)
    expect(url).toBe('ws://localhost:5173/ws/replay/abc?token=abc')
  })

  it('rejects absolute WS URLs pointing at a foreign host', () => {
    expect(() =>
      resolveReplayWsBase('wss://evil.example.com/x', {
        protocol: 'https:',
        host: 'app.example.com',
      } as Location),
    ).toThrow(/foreign host/i)
  })

  it('allows same-origin absolute WS URLs', () => {
    expect(
      resolveReplayWsBase('wss://app.example.com/ws/replay/abc', {
        protocol: 'https:',
        host: 'app.example.com',
      } as Location),
    ).toBe('wss://app.example.com/ws/replay/abc')
  })

  it('dispatches typed events and serializes send', async () => {
    const client = new ReplayWsClient()
    const onEvent = vi.fn()
    void client.connect('/ws/replay/x', { onEvent })
    const socket = await waitForSocket()
    socket.open()
    socket.emit({
      type: 'buffer_loading',
    })
    expect(onEvent).toHaveBeenCalledWith({ type: 'buffer_loading' })

    client.send({ action: 'step', count: 1 })
    expect(JSON.parse(socket.sent[0]!)).toEqual({ action: 'step', count: 1 })
  })

  it('maps distinct close codes for auth, superseded, not_found, rate_limited', async () => {
    async function closeWith(code: number, reason: string) {
      const priorCount = MockWebSocket.instances.length
      const client = new ReplayWsClient()
      const onClose = vi.fn()
      void client.connect('/ws/replay/x', { onClose })
      const socket = await waitForSocket(priorCount)
      socket.open()
      socket.close(code, reason)
      return onClose
    }

    expect(await closeWith(4401, 'UNAUTHORIZED')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4401, kind: 'unauthorized' }),
    )
    expect(await closeWith(4402, 'SUPERSEDED')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4402, kind: 'superseded' }),
    )
    expect(await closeWith(4404, 'missing')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4404, kind: 'not_found' }),
    )
    expect(await closeWith(4429, 'WS_LIMIT')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4429, kind: 'rate_limited' }),
    )
  })

  it('queues commands until socket opens then flushes', async () => {
    const client = new ReplayWsClient()
    void client.connect('/ws/replay/x')
    const socket = await waitForSocket()
    client.send({ action: 'play', speed: 1 })
    expect(socket.sent).toHaveLength(0)
    expect(client.queuedCount).toBe(1)
    socket.open()
    expect(JSON.parse(socket.sent[0]!)).toEqual({ action: 'play', speed: 1 })
    expect(client.consumePendingPlay()).toBe(true)
  })
})
