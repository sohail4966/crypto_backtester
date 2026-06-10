import { useEffect, useMemo, useRef, useState } from 'react'
import { useIndicatorCatalog } from '@/hooks/useIndicatorCatalog'
import { useIndicatorStore } from '@/stores/indicatorStore'
import {
  isMacdKey,
  type IndicatorCatalogEntry,
  type IndicatorPane,
} from '@/types/indicator'
import { indicatorSeriesId } from '@/utils/indicatorId'

const QUICK_KEYS = new Set(['EMA', 'SMA', 'RSI', 'MACD_LINE'])

function normalizeCatalogEntry(row: Record<string, unknown>): IndicatorCatalogEntry {
  return {
    key: String(row.key),
    inputs: (row.inputs as string[]) ?? [],
    sharedParams: (row.shared_params as string[]) ?? (row.sharedParams as string[]) ?? [],
    defaultParams:
      (row.default_params as Record<string, unknown>) ??
      (row.defaultParams as Record<string, unknown>) ??
      {},
    pane: (row.pane as IndicatorPane) ?? 'overlay',
  }
}

function pickerLabel(entry: IndicatorCatalogEntry): string {
  if (isMacdKey(entry.key)) {
    return 'MACD'
  }
  const period = entry.defaultParams.period
  return period != null ? `${entry.key} (${period})` : entry.key
}

interface IndicatorPanelProps {
  open: boolean
  onClose: () => void
}

export function IndicatorPanel({ open, onClose }: IndicatorPanelProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const catalogQuery = useIndicatorCatalog()
  const addFromCatalog = useIndicatorStore((state) => state.addFromCatalog)
  const active = useIndicatorStore((state) => state.active)
  const [filter, setFilter] = useState('')

  const activeSeriesIds = useMemo(
    () => new Set(active.map((item) => item.seriesId)),
    [active],
  )

  const entries = useMemo(() => {
    const rows = (catalogQuery.data ?? []).map((entry) =>
      typeof entry === 'object' && entry != null && 'key' in entry
        ? normalizeCatalogEntry(entry as unknown as Record<string, unknown>)
        : (entry as IndicatorCatalogEntry),
    )

    const seen = new Set<string>()
    const picked: IndicatorCatalogEntry[] = []
    for (const entry of rows) {
      if (!QUICK_KEYS.has(entry.key)) {
        continue
      }
      const label = isMacdKey(entry.key) ? 'MACD' : entry.key
      if (seen.has(label)) {
        continue
      }
      seen.add(label)
      picked.push(entry)
    }
    return picked.sort((a, b) => a.key.localeCompare(b.key))
  }, [catalogQuery.data])

  const filtered = entries.filter((entry) =>
    pickerLabel(entry).toLowerCase().includes(filter.toLowerCase()),
  )

  useEffect(() => {
    if (!open) {
      return
    }

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [onClose, open])

  if (!open) {
    return null
  }

  return (
    <div
      ref={rootRef}
      className="absolute left-0 top-full z-50 mt-1 w-72 rounded border border-border bg-surface p-2 shadow-lg"
    >
      <input
        type="search"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Search indicators…"
        className="mb-2 w-full rounded border border-border bg-bg px-2 py-1.5 text-xs text-text outline-none"
      />

      {catalogQuery.isPending ? (
        <p className="px-2 py-3 text-xs text-text-secondary">Loading catalog…</p>
      ) : null}

      {catalogQuery.isError ? (
        <p className="px-2 py-3 text-xs text-bear">Failed to load indicator catalog.</p>
      ) : null}

      <ul className="max-h-64 overflow-auto">
        {filtered.map((entry) => {
          const disabled = isMacdKey(entry.key)
            ? active.some((item) => isMacdKey(item.key))
            : activeSeriesIds.has(indicatorSeriesId(entry.key, entry.defaultParams))

          return (
            <li key={entry.key}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  addFromCatalog(entry)
                  onClose()
                }}
                className="flex w-full items-center justify-between rounded px-2 py-2 text-left text-xs transition-colors hover:bg-bg disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span className="font-medium text-text">{pickerLabel(entry)}</span>
                <span className="text-text-secondary">{entry.pane}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
