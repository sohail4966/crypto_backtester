import { useEffect, useMemo, useRef, useState } from 'react'
import { useIndicatorCatalog } from '@/hooks/useIndicatorCatalog'
import { useIndicatorStore } from '@/stores/indicatorStore'
import { MAX_SUB_PANES } from '@/constants/chart'
import type { IndicatorCatalogEntry } from '@/types/indicator'
import {
  catalogPickerLabel,
  normalizeCatalogEntry,
  pickerCatalogEntries,
} from '@/utils/indicatorCatalog'

interface IndicatorPanelProps {
  open: boolean
  onClose: () => void
}

function countSubchartInstances(active: { pane: string; groupInstanceId: string }[]): number {
  const ids = new Set<string>()
  for (const item of active) {
    if (item.pane === 'subchart') {
      ids.add(item.groupInstanceId)
    }
  }
  return ids.size
}

export function IndicatorPanel({ open, onClose }: IndicatorPanelProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const catalogQuery = useIndicatorCatalog()
  const addFromCatalog = useIndicatorStore((state) => state.addFromCatalog)
  const active = useIndicatorStore((state) => state.active)
  const [filter, setFilter] = useState('')
  const [error, setError] = useState<string | null>(null)

  const subchartCount = useMemo(() => countSubchartInstances(active), [active])
  const atSubPaneLimit = subchartCount >= MAX_SUB_PANES

  const entries = useMemo(() => {
    const rows = (catalogQuery.data ?? []).map((entry) =>
      normalizeCatalogEntry(entry as unknown as Record<string, unknown>),
    )
    return pickerCatalogEntries(rows)
  }, [catalogQuery.data])

  const filtered = entries.filter((entry) =>
    catalogPickerLabel(entry).toLowerCase().includes(filter.toLowerCase()),
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

  useEffect(() => {
    if (!open) {
      setError(null)
    }
  }, [open])

  if (!open) {
    return null
  }

  function isDisabled(entry: IndicatorCatalogEntry): boolean {
    return entry.pane === 'subchart' && atSubPaneLimit
  }

  return (
    <div
      ref={rootRef}
      className="absolute left-0 top-full z-50 mt-1 w-80 rounded border border-border bg-surface p-2 shadow-lg"
    >
      <input
        type="search"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Search indicators…"
        className="mb-2 w-full rounded border border-border bg-bg px-2 py-1.5 text-xs text-text outline-none"
      />

      {atSubPaneLimit ? (
        <p className="mb-2 px-1 text-[10px] text-text-secondary">
          Sub-chart limit: {MAX_SUB_PANES} panes (e.g. RSI, MACD). Remove one to add another.
        </p>
      ) : null}

      {error ? <p className="mb-2 px-1 text-xs text-bear">{error}</p> : null}

      {catalogQuery.isPending ? (
        <p className="px-2 py-3 text-xs text-text-secondary">Loading catalog…</p>
      ) : null}

      {catalogQuery.isError ? (
        <p className="px-2 py-3 text-xs text-bear">Failed to load indicator catalog.</p>
      ) : null}

      <ul className="max-h-72 overflow-auto">
        {filtered.map((entry) => {
          const disabled = isDisabled(entry)

          return (
            <li key={entry.key}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  const result = addFromCatalog(entry)
                  if (!result.ok) {
                    setError(result.error)
                    return
                  }
                  setError(null)
                  onClose()
                }}
                className="flex w-full items-center justify-between rounded px-2 py-2 text-left text-xs transition-colors hover:bg-bg disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span className="font-medium text-text">{catalogPickerLabel(entry)}</span>
                <span className="text-text-secondary">{entry.pane}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
