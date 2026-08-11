import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LiveWsClient, resolveLiveWsBase } from '@/services/liveWsClient'
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

async function waitForSocket(sinceCount = 0): Promise<MockWebSocket> {
  for (let i = 0; i < 40; i += 1) {
    if (MockWebSocket.instances.length > sinceCount) {
      return MockWebSocket.instances[MockWebSocket.instances.length - 1]!
    }
    await Promise.resolve()
  }
  throw new Error('MockWebSocket was never constructed')
}

describe('liveWsClient', () => {
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

  it('resolveLiveWsBase builds ws:// from window.location by default', () => {
    expect(
      resolveLiveWsBase({
        protocol: 'https:',
        host: 'app.example.com',
      } as Location),
    ).toBe('wss://app.example.com/ws/live')
  })

  it('resolveLiveWsBase rejects a configured foreign-host absolute URL', () => {
    vi.stubEnv('VITE_LIVE_WS_URL', 'wss://evil.example.com/ws/live')
    expect(() =>
      resolveLiveWsBase({
        protocol: 'https:',
        host: 'app.example.com',
      } as Location),
    ).toThrow(/foreign host/i)
    vi.unstubAllEnvs()
  })

  it('reads `row.bar` and emits an OHLCVBar payload', async () => {
    setAuthToken('jwt-abc')
    const client = new LiveWsClient()
    const onCandle = vi.fn()
    void client.connect({ onCandle })
    const socket = await waitForSocket()
    socket.open()
    socket.emit({
      type: 'candle',
      symbol: 'BTC/USDT',
      timeframe: '1m',
      bar: {
        time: 1_700_000_000,
        open: 30000,
        high: 30100,
        low: 29900,
        close: 30050,
        volume: 12.5,
      },
    })
    expect(onCandle).toHaveBeenCalledWith({
      symbol: 'BTC/USDT',
      timeframe: '1m',
      bar: {
        time: 1_700_000_000,
        open: 30000,
        high: 30100,
        low: 29900,
        close: 30050,
        volume: 12.5,
      },
    })
  })

  it('ignores legacy `row.candle` payloads (contract truthing)', async () => {
    setAuthToken('jwt-abc')
    const client = new LiveWsClient()
    const onCandle = vi.fn()
    void client.connect({ onCandle })
    const socket = await waitForSocket()
    socket.open()
    socket.emit({
      type: 'candle',
      symbol: 'BTC/USDT',
      timeframe: '1m',
      candle: { time: 1, open: 1, high: 1, low: 1, close: 1, volume: 1 },
    })
    expect(onCandle).not.toHaveBeenCalled()
  })

  it('surfaces close.code via onClose with the shared kind classifier', async () => {
    async function closeWith(code: number, reason: string) {
      const priorCount = MockWebSocket.instances.length
      const client = new LiveWsClient()
      const onClose = vi.fn()
      void client.connect({ onClose })
      const socket = await waitForSocket(priorCount)
      socket.open()
      socket.close(code, reason)
      return onClose
    }

    expect(await closeWith(4401, 'UNAUTHORIZED')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4401, kind: 'unauthorized' }),
    )
    expect(await closeWith(4429, 'WS_LIMIT')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 4429, kind: 'rate_limited' }),
    )
    expect(await closeWith(1000, '')).toHaveBeenCalledWith(
      expect.objectContaining({ code: 1000, kind: 'closed' }),
    )
  })
})
