import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SymbolSearch } from '@/components/Watchlist/SymbolSearch'
import { ToastProvider } from '@/components/ui/Toast'
import { useChartStore } from '@/stores/chartStore'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { Watchlist } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'

const addSymbolToSelected = vi.fn()
const searchSymbols = vi.fn()

vi.mock('@/services/chartDataAdapter', () => ({
  searchSymbols: (...args: unknown[]) => searchSymbols(...args),
}))

vi.mock('@/components/Watchlist/WatchlistRoot', () => ({
  useWatchlistSession: () => ({
    retry: vi.fn(),
    createWatchlist: vi.fn(),
    addSymbolToSelected,
    isAddPending: () => useWatchlistStore.getState().pendingWatchlistIds.length > 0,
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

const eth: Symbol = {
  ...btc,
  id: 'ETH/USDT',
  ticker: 'ETH/USDT',
  baseAsset: 'ETH',
  type: 'perp',
  sortOrder: 2,
}

function list(overrides: Partial<Watchlist> = {}): Watchlist {
  return {
    id: 'wl-1',
    userId: 'user-1',
    name: 'Default',
    isDefault: true,
    sortOrder: 0,
    symbols: [],
    createdAt: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderSearch() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SymbolSearch />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

async function openCatalog() {
  fireEvent.focus(screen.getByLabelText('Search symbols'))
  await waitFor(() => {
    expect(searchSymbols).toHaveBeenCalled()
  })
  await waitFor(() => {
    expect(screen.getByText('BTC/USDT')).toBeInTheDocument()
  })
}

describe('SymbolSearch', () => {
  beforeEach(() => {
    useChartStore.setState({ symbol: null })
    useWatchlistStore.getState().reset()
    useWatchlistStore.getState().applyCanonical([list()], 'wl-1')
    searchSymbols.mockReset()
    addSymbolToSelected.mockReset()
    searchSymbols.mockResolvedValue([btc, eth])
    addSymbolToSelected.mockResolvedValue(true)
  })

  it('requests empty-query catalog on focus and debounces typed queries by 250 ms', async () => {
    vi.useFakeTimers()
    try {
      renderSearch()
      fireEvent.focus(screen.getByLabelText('Search symbols'))

      // Initial empty debounced value enables immediately when open.
      await act(async () => {
        await Promise.resolve()
      })
      expect(searchSymbols).toHaveBeenCalledWith('')

      searchSymbols.mockClear()
      fireEvent.change(screen.getByLabelText('Search symbols'), {
        target: { value: 'eth' },
      })
      expect(searchSymbols).not.toHaveBeenCalled()

      await act(async () => {
        vi.advanceTimersByTime(249)
        await Promise.resolve()
      })
      expect(searchSymbols).not.toHaveBeenCalled()

      await act(async () => {
        vi.advanceTimersByTime(1)
        await Promise.resolve()
      })
      expect(searchSymbols).toHaveBeenCalledWith('eth')
    } finally {
      vi.useRealTimers()
    }
  })

  it('trims queries and treats whitespace as empty', async () => {
    renderSearch()
    const input = screen.getByLabelText('Search symbols')
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: '   ' } })
    await waitFor(() => {
      expect(searchSymbols).toHaveBeenCalledWith('')
    })
  })

  it('renders ticker, exchange, type, and supports selection + add', async () => {
    renderSearch()
    await openCatalog()
    expect(screen.getAllByText('binance').length).toBeGreaterThan(0)
    expect(screen.getByText('spot')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('option', { name: /ETH\/USDT/ }))
    expect(useChartStore.getState().symbol?.id).toBe('ETH/USDT')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('Add targets the selected watchlist without switching chart or closing results', async () => {
    useChartStore.setState({ symbol: btc })
    renderSearch()
    await openCatalog()

    fireEvent.click(screen.getByRole('button', { name: 'Add ETH/USDT to Default' }))
    await waitFor(() => {
      expect(addSymbolToSelected).toHaveBeenCalledWith(eth)
    })
    expect(useChartStore.getState().symbol?.id).toBe('BTC/USDT')
    expect(screen.getByRole('listbox')).toBeInTheDocument()
  })

  it('existing symbol shows Added and makes no PUT', async () => {
    useWatchlistStore.getState().applyCanonical([list({ symbols: [btc] })], 'wl-1')
    renderSearch()
    await openCatalog()

    expect(screen.getByRole('button', { name: /already in Default/ })).toHaveTextContent(
      'Added',
    )
    fireEvent.click(screen.getByRole('button', { name: /already in Default/ }))
    expect(addSymbolToSelected).not.toHaveBeenCalled()
  })

  it('failed add reports an error toast', async () => {
    addSymbolToSelected.mockRejectedValueOnce(new Error('PUT failed'))
    renderSearch()
    await openCatalog()
    fireEvent.click(screen.getByRole('button', { name: 'Add ETH/USDT to Default' }))
    expect(await screen.findByText('PUT failed')).toBeInTheDocument()
  })
})
