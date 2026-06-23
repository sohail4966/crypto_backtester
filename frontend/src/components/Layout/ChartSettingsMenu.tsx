import { useEffect, useRef, useState } from 'react'
import { useChartStore } from '@/stores/chartStore'

interface ChartSettingsMenuProps {
  layout?: 'topbar' | 'sidebar'
}

function SettingsIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function ChartSettingsMenu({ layout = 'topbar' }: ChartSettingsMenuProps) {
  const showGrid = useChartStore((state) => state.showGrid)
  const setShowGrid = useChartStore((state) => state.setShowGrid)
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const inSidebar = layout === 'sidebar'

  useEffect(() => {
    if (!open) {
      return
    }

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [open])

  return (
    <div ref={rootRef} className={inSidebar ? 'relative w-full' : 'relative'}>
      <button
        type="button"
        aria-label="Chart settings"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={[
          inSidebar
            ? 'flex w-full items-center gap-2 rounded border border-border px-2 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text'
            : 'rounded border border-border p-1.5 text-text-secondary transition-colors hover:border-accent/40 hover:text-text',
          open ? 'border-accent/40 text-text' : '',
        ].join(' ')}
      >
        <SettingsIcon />
        {inSidebar ? <span>Chart settings</span> : null}
      </button>

      {open ? (
        <div
          className={[
            'absolute z-50 min-w-[10rem] rounded border border-border bg-surface p-2 shadow-lg',
            inSidebar ? 'bottom-full left-0 mb-1' : 'right-0 top-full mt-1',
          ].join(' ')}
        >
          <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-xs text-text hover:bg-bg">
            <input
              type="checkbox"
              checked={showGrid}
              onChange={(event) => setShowGrid(event.target.checked)}
              className="accent-accent"
            />
            <span>Show grid on all panes</span>
          </label>
        </div>
      ) : null}
    </div>
  )
}
