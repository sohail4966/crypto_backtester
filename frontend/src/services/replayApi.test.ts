import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  normalizeCreateResponse,
  normalizeSessionMeta,
  normalizeSnapshot,
  normalizeWsInbound,
} from '@/utils/replayNormalize'
import { createReplaySession, deleteReplaySession, getReplaySession } from '@/services/replayApi'
import { ApiError } from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

import { apiRequest } from '@/services/api'

describe('replay normalize', () => {
  it('maps session_id/ws_url to camelCase', () => {
    expect(
      normalizeCreateResponse({
        session_id: 'abc',
        ws_url: '/ws/replay/abc',
      }),
    ).toEqual({ sessionId: 'abc', wsUrl: '/ws/replay/abc' })
  })

  it('accepts camel create response aliases', () => {
    expect(
      normalizeCreateResponse({
        sessionId: 'abc',
        wsUrl: '/ws/replay/abc',
      }),
    ).toEqual({ sessionId: 'abc', wsUrl: '/ws/replay/abc' })
  })

  it('tolerates snake and camel for GET/state fields', () => {
    const snake = normalizeSessionMeta({
      session_id: 's1',
      symbol: 'BTC/USDT',
      timeframe: '1h',
      step_timeframe: '1h',
      start: 100,
      latest_available: 200,
      cursor: 90,
      state: 'paused',
      speed: 1,
      bar_index: 0,
      queue_remaining: 50,
      indicators: [],
    })
    expect(snake.startAnchor).toBe(100)
    expect(snake.latestAvailable).toBe(200)
    expect(snake.barIndex).toBe(0)
    expect(snake.queueRemaining).toBe(50)
    expect(snake.stepTimeframe).toBe('1h')

    const camel = normalizeSessionMeta({
      sessionId: 's1',
      symbol: 'BTC/USDT',
      timeframe: '1h',
      stepTimeframe: '1h',
      startAnchor: 100,
      latestAvailable: 200,
      cursor: 90,
      state: 'paused',
      speed: 2,
      barIndex: 3,
      queueRemaining: 10,
      indicators: [{ key: 'EMA', params: { period: 20 }, pane: 'overlay' }],
    })
    expect(camel.startAnchor).toBe(100)
    expect(camel.barIndex).toBe(3)
    expect(camel.indicators[0]?.key).toBe('EMA')
  })

  it('normalizes empty snapshot', () => {
    const snap = normalizeSnapshot({
      type: 'snapshot',
      bars: [],
      indicators: {},
      cursor: 90,
      startAnchor: 100,
      latestAvailable: 200,
    })
    expect(snap.bars).toEqual([])
    expect(snap.cursor).toBe(90)
  })

  it('normalizes tick_batch inbound', () => {
    const event = normalizeWsInbound({
      type: 'tick_batch',
      ticks: [
        {
          bar: {
            time: 100,
            open: 1,
            high: 2,
            low: 0.5,
            close: 1.5,
            volume: 10,
          },
          indicators: { EMA_20: { time: 100, value: 1.2 } },
        },
      ],
      cursor: 100,
      queue_remaining: 87,
    })
    expect(event?.type).toBe('tick_batch')
    if (event?.type === 'tick_batch') {
      expect(event.ticks).toHaveLength(1)
      expect(event.queueRemaining).toBe(87)
    }
  })
})

describe('replayApi', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset()
  })

  it('createReplaySession posts snake body and normalizes response', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      session_id: 'sid',
      ws_url: '/ws/replay/sid',
    })
    const result = await createReplaySession({
      symbol: 'BTC/USDT',
      timeframe: '1h',
      start: 100,
      indicators: [],
      speed: 1,
      autoplay: false,
    })
    expect(result).toEqual({ sessionId: 'sid', wsUrl: '/ws/replay/sid' })
    expect(apiRequest).toHaveBeenCalledWith(
      '/replay/sessions',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('getReplaySession normalizes meta', async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      session_id: 'sid',
      symbol: 'BTC/USDT',
      timeframe: '1h',
      start_anchor: 100,
      state: 'paused',
      speed: 1,
    })
    const meta = await getReplaySession('sid')
    expect(meta.sessionId).toBe('sid')
    expect(meta.startAnchor).toBe(100)
  })

  it('deleteReplaySession swallows 404', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new ApiError(404, 'not found'))
    await expect(deleteReplaySession('missing')).resolves.toBeUndefined()
  })
})
