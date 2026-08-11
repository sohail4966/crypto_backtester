import { useState } from 'react'
import type { SyncConfig } from '@/types/workspace'
import { useWorkspaceStore } from '@/stores/workspaceStore'

const SYNC_LABELS: { key: keyof SyncConfig; label: string }[] = [
  { key: 'crosshair', label: 'Crosshair' },
  { key: 'visibleRange', label: 'Visible range' },
  { key: 'symbol', label: 'Symbol' },
  { key: 'timeframe', label: 'Timeframe' },
]

export function SyncConfigPanel() {
  const [open, setOpen] = useState(false)
  const sync = useWorkspaceStore((s) => s.sync)
  const setSyncCategory = useWorkspaceStore((s) => s.setSyncCategory)

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((prev) => !prev)}
        className="rounded border border-border px-2.5 py-1 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text"
      >
        Sync
      </button>
      {open ? (
        <div
          className="absolute right-0 z-30 mt-1 min-w-[180px] rounded border border-border bg-surface p-2 shadow-lg"
          role="dialog"
          aria-label="Chart sync settings"
        >
          <p className="mb-2 px-1 text-[11px] uppercase tracking-wide text-text-secondary">
            Sync panes
          </p>
          <p className="mb-2 px-1 text-[10px] leading-snug text-text-secondary">
            Visible range only applies across panes that share a symbol unless
            Symbol sync is on.
          </p>
          <ul className="flex flex-col gap-1">
            {SYNC_LABELS.map(({ key, label }) => (
              <li key={key}>
                <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-xs text-text hover:bg-bg">
                  <input
                    type="checkbox"
                    checked={sync[key]}
                    onChange={(event) =>
                      setSyncCategory(key, event.target.checked)
                    }
                  />
                  {label}
                </label>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
