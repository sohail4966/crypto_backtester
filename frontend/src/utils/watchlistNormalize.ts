import { SYMBOL_RESOLVE_CONCURRENCY } from '@/constants/watchlist'
import { getSymbol, searchSymbols } from '@/services/chartDataAdapter'
import type { Watchlist, WatchlistDto } from '@/types/watchlist'
import type { Symbol } from '@/types/symbol'

export class SymbolResolveError extends Error {
  readonly unresolvedIds: string[]

  constructor(unresolvedIds: string[]) {
    super(`Unable to resolve symbol IDs: ${unresolvedIds.join(', ')}`)
    this.name = 'SymbolResolveError'
    this.unresolvedIds = unresolvedIds
  }
}

function asString(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  if (value == null) {
    return ''
  }
  return String(value)
}

export function mapWatchlistDto(dto: WatchlistDto, symbols: Symbol[]): Watchlist {
  return {
    id: asString(dto.id),
    userId: asString(dto.user_id),
    name: dto.name,
    isDefault: Boolean(dto.is_default),
    sortOrder: Number(dto.sort_order),
    symbols,
    createdAt: asString(dto.created_at),
  }
}

async function mapPool<T, R>(
  items: T[],
  concurrency: number,
  mapper: (item: T) => Promise<R>,
): Promise<R[]> {
  if (items.length === 0) {
    return []
  }
  const results = new Array<R>(items.length)
  let nextIndex = 0

  async function worker() {
    while (nextIndex < items.length) {
      const index = nextIndex
      nextIndex += 1
      results[index] = await mapper(items[index] as T)
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => worker(),
  )
  await Promise.all(workers)
  return results
}

/**
 * Resolve ordered symbol IDs via active catalog, then concurrent getSymbol fallbacks.
 * Fails the entire refresh if any ID remains unresolved.
 */
export async function resolveWatchlistDtos(
  dtos: WatchlistDto[],
  deps: {
    searchSymbols?: typeof searchSymbols
    getSymbol?: typeof getSymbol
  } = {},
): Promise<Watchlist[]> {
  const catalogSearch = deps.searchSymbols ?? searchSymbols
  const fetchSymbol = deps.getSymbol ?? getSymbol

  const needsResolution = dtos.some((dto) => dto.symbols.length > 0)
  if (!needsResolution) {
    return dtos.map((dto) => mapWatchlistDto(dto, []))
  }

  const catalog = await catalogSearch('')
  const byId = new Map<string, Symbol>()
  for (const symbol of catalog) {
    byId.set(symbol.id, symbol)
  }

  const missing = new Set<string>()
  for (const dto of dtos) {
    for (const id of dto.symbols) {
      if (!byId.has(id)) {
        missing.add(id)
      }
    }
  }

  const unresolved: string[] = []
  if (missing.size > 0) {
    const ids = [...missing]
    const fetched = await mapPool(ids, SYMBOL_RESOLVE_CONCURRENCY, async (id) => {
      try {
        return await fetchSymbol(id)
      } catch {
        return null
      }
    })
    for (let i = 0; i < ids.length; i += 1) {
      const symbol = fetched[i]
      const id = ids[i] as string
      if (symbol) {
        byId.set(symbol.id, symbol)
      } else {
        unresolved.push(id)
      }
    }
  }

  if (unresolved.length > 0) {
    throw new SymbolResolveError(unresolved)
  }

  return dtos.map((dto) => {
    const symbols = dto.symbols.map((id) => {
      const symbol = byId.get(id)
      if (!symbol) {
        throw new SymbolResolveError([id])
      }
      return symbol
    })
    return mapWatchlistDto(dto, symbols)
  })
}

/**
 * Prefer a still-valid selection; else isDefault; else lowest sortOrder (response
 * order for ties); else null.
 */
export function selectWatchlistId(
  watchlists: Watchlist[],
  preferredId: string | null,
): string | null {
  if (preferredId && watchlists.some((list) => list.id === preferredId)) {
    return preferredId
  }

  const defaultList = watchlists.find((list) => list.isDefault)
  if (defaultList) {
    return defaultList.id
  }

  if (watchlists.length === 0) {
    return null
  }

  let best = watchlists[0] as Watchlist
  for (const list of watchlists.slice(1)) {
    if (list.sortOrder < best.sortOrder) {
      best = list
    }
  }
  return best.id
}
