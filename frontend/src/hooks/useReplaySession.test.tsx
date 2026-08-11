import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useSearchParams } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useReplaySession } from '@/hooks/useReplaySession'
import { useChartStore } from '@/stores/chartStore'
import { useReplayStore } from '@/stores/replayStore'
import { REPLAY_SESSION_QUERY } from '@/constants/replay'

vi.mock('@/services/replayApi', () => ({
  createReplaySession: vi.fn(),
  getReplaySession: vi.fn(),
  deleteReplaySession: vi.fn(async () => undefined),
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

import {
  createReplaySession,
  deleteReplaySession,
  getReplaySession,
} from '@/services/replayApi'

function wrapper(initialEntry = '/') {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[initialEntry]}>{children}</MemoryRouter>
  }
}

describe('useReplaySession', () => {
  beforeEach(() => {
    useReplayStore.getState().reset()
    useChartStore.setState({
      symbol: {
        id: 'BTC/USDT',
        ticker: 'BTC/USDT',
        exchange: 'binance',
        baseAsset: 'BTC',
        quoteAsset: 'USDT',
        tickSize: 0.01,
        lotSize: 0.00001,
        type: 'spot',
        active: true,
        sortOrder: 1,
      },
      timeframe: '1h',
      replayMode: false,
    })
    vi.mocked(createReplaySession).mockReset()
    vi.mocked(getReplaySession).mockReset()
    vi.mocked(deleteReplaySession).mockReset()
    vi.mocked(deleteReplaySession).mockResolvedValue(undefined)
  })

  it('create writes URL param', async () => {
    vi.mocked(createReplaySession).mockResolvedValue({
      sessionId: 'new-session',
      wsUrl: '/ws/replay/new-session',
    })

    const { result } = renderHook(
      () => {
        const session = useReplaySession()
        const [params] = useSearchParams()
        return { session, replaySession: params.get(REPLAY_SESSION_QUERY) }
      },
      { wrapper: wrapper() },
    )

    await act(async () => {
      await result.current.session.startFromAnchor(1_700_000_000)
    })

    await waitFor(() => {
      expect(result.current.replaySession).toBe('new-session')
    })
    expect(useChartStore.getState().replayMode).toBe(true)
  })

  it('teardown clears URL and Stop → pick_anchor with mode on', async () => {
    vi.mocked(createReplaySession).mockResolvedValue({
      sessionId: 'sid',
      wsUrl: '/ws/replay/sid',
    })

    const { result } = renderHook(
      () => {
        const session = useReplaySession()
        const [params] = useSearchParams()
        return { session, replaySession: params.get(REPLAY_SESSION_QUERY) }
      },
      { wrapper: wrapper() },
    )

    await act(async () => {
      await result.current.session.startFromAnchor(100)
    })

    await act(async () => {
      await result.current.session.stopToPickAnchor()
    })

    await waitFor(() => {
      expect(result.current.replaySession).toBeNull()
    })
    expect(useReplayStore.getState().phase).toBe('pick_anchor')
    expect(useChartStore.getState().replayMode).toBe(true)
    expect(deleteReplaySession).toHaveBeenCalled()
  })

  it('invalid resume toasts and clears param', async () => {
    vi.mocked(getReplaySession).mockRejectedValue(new Error('404'))

    const { result } = renderHook(
      () => {
        const session = useReplaySession()
        const [params] = useSearchParams()
        return { session, replaySession: params.get(REPLAY_SESSION_QUERY) }
      },
      { wrapper: wrapper('/?replaySession=missing') },
    )

    await waitFor(() => {
      expect(result.current.replaySession).toBeNull()
    })
    expect(useChartStore.getState().replayMode).toBe(false)
  })
})
