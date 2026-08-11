import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WatchlistPanel } from '@/components/Watchlist/WatchlistPanel'
import { WatchlistRow } from '@/components/Watchlist/WatchlistRow'
import { ToastProvider } from '@/components/ui/Toast'
import { useChartStore } from '@/stores/chartStore'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { Watchlist } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'

const createWatchlist = vi.fn()
const retry = vi.fn()

vi.mock('@/components/Watchlist/WatchlistRoot', () => ({
  useWatchlistSession: () => ({
    retry,
    createWatchlist,
    addSymbolToSelected: vi.fn(),
    isAddPending: () => false,
  }),
}))

const btc: Symbol = {
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
}

function list(overrides: Partial<Watchlist> = {}): Watchlist {
  return {
    id: 'wl-1',
    userId: 'user-1',
    name: 'Default',
    isDefault: true,
    sortOrder: 0,
    symbols: [btc],
    createdAt: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPanel() {
  return render(
    <ToastProvider>
      <WatchlistPanel />
    </ToastProvider>,
  )
}

describe('WatchlistPanel / WatchlistRow', () => {
  beforeEach(() => {
    useWatchlistStore.getState().reset()
    useChartStore.setState({ symbol: null })
    createWatchlist.mockReset()
    retry.mockReset()
  })

  it('renders loading, empty, stale-cache, hard-error, and Retry states', () => {
    useWatchlistStore.setState({ status: 'bootstrapping', watchlists: [] })
    const { rerender } = renderPanel()
    expect(screen.getByText('Loading watchlists…')).toBeInTheDocument()

    act(() => {
      useWatchlistStore.setState({
        status: 'ready',
        watchlists: [list({ symbols: [] })],
        selectedWatchlistId: 'wl-1',
        stale: false,
      })
    })
    rerender(
      <ToastProvider>
        <WatchlistPanel />
      </ToastProvider>,
    )
    expect(screen.getByText(/No symbols yet/)).toBeInTheDocument()

    act(() => {
      useWatchlistStore.setState({
        status: 'refreshing',
        stale: true,
        errorMessage: null,
      })
    })
    rerender(
      <ToastProvider>
        <WatchlistPanel />
      </ToastProvider>,
    )
    expect(screen.getByText(/Showing cached watchlist — refreshing/)).toBeInTheDocument()

    act(() => {
      useWatchlistStore.setState({
        status: 'ready',
        watchlists: [list()],
        selectedWatchlistId: 'wl-1',
        stale: true,
        errorMessage: 'Refresh failed',
      })
    })
    rerender(
      <ToastProvider>
        <WatchlistPanel />
      </ToastProvider>,
    )
    expect(screen.getByText('Refresh failed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()

    act(() => {
      useWatchlistStore.setState({
        status: 'error',
        watchlists: [],
        selectedWatchlistId: null,
        errorMessage: 'Network down',
        stale: false,
      })
    })
    rerender(
      <ToastProvider>
        <WatchlistPanel />
      </ToastProvider>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Network down')
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('renders selector and creates a trimmed valid list', async () => {
    useWatchlistStore.setState({
      status: 'ready',
      watchlists: [list()],
      selectedWatchlistId: 'wl-1',
    })
    createWatchlist.mockResolvedValue(
      list({ id: 'wl-2', name: 'Alts', isDefault: false }),
    )

    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'New' }))
    fireEvent.change(screen.getByLabelText('New watchlist name'), {
      target: { value: '  Alts  ' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    })
    expect(createWatchlist).toHaveBeenCalledWith('Alts')
  })

  it('row click passes the complete Symbol to chartStore.setSymbol', () => {
    useChartStore.setState({ symbol: null })
    render(<WatchlistRow symbol={btc} />)
    fireEvent.click(screen.getByRole('button', { name: /BTC\/USDT/ }))
    expect(useChartStore.getState().symbol).toEqual(btc)
  })

  it('marks the active row and shows price placeholder', () => {
    useChartStore.setState({ symbol: btc })
    render(<WatchlistRow symbol={btc} />)
    const row = screen.getByRole('button', { name: /BTC\/USDT/ })
    expect(row).toHaveAttribute('aria-current', 'true')
    expect(row).toHaveTextContent('—')
  })
})
