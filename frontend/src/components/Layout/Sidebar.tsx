import { NavLink } from 'react-router-dom'
import { ChartSettingsMenu } from '@/components/Layout/ChartSettingsMenu'
import { TimezoneSelector } from '@/components/Layout/TimezoneSelector'
import { useLayoutStore } from '@/stores/layoutStore'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'block rounded px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-accent/15 text-accent'
      : 'text-text-secondary hover:bg-bg hover:text-text',
  ].join(' ')

function CollapseIcon() {
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
      <path d="M15 18l-6-6 6-6" />
    </svg>
  )
}

export function Sidebar() {
  const sidebarOpen = useLayoutStore((state) => state.sidebarOpen)
  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar)

  return (
    <aside
      className={[
        'flex shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 ease-in-out',
        sidebarOpen ? 'w-52' : 'w-0 overflow-hidden border-r-0',
      ].join(' ')}
      aria-hidden={!sidebarOpen}
    >
      <div className="flex w-52 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-border px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Workspace
          </p>
          <button
            type="button"
            aria-label="Hide sidebar"
            onClick={toggleSidebar}
            className="rounded p-1 text-text-secondary transition-colors hover:bg-bg hover:text-text"
          >
            <CollapseIcon />
          </button>
        </div>

        <nav className="flex flex-col gap-1 p-3" aria-label="Main">
          <NavLink to="/" end className={navLinkClass}>
            Chart
          </NavLink>
          <NavLink to="/replay" className={navLinkClass}>
            Replay
          </NavLink>
          <NavLink to="/backtest" className={navLinkClass}>
            Backtest
          </NavLink>
        </nav>

        <div className="mt-auto border-t border-border p-3">
          <div className="flex flex-col gap-3">
            <TimezoneSelector layout="sidebar" />
            <ChartSettingsMenu layout="sidebar" />
          </div>
        </div>
      </div>
    </aside>
  )
}
