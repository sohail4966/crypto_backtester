import { useLocation } from 'react-router-dom'
import { IndicatorsBar } from '@/components/Layout/IndicatorsBar'
import { TimeframeSelector } from '@/components/Layout/TimeframeSelector'
import { SymbolSearch } from '@/components/Watchlist/SymbolSearch'
import { useTheme } from '@/hooks/useTheme'
import { useLayoutStore } from '@/stores/layoutStore'

function SidebarToggleIcon() {
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
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  )
}

export function Topbar() {
  const location = useLocation()
  const onChartRoute = location.pathname === '/'
  const { theme, toggleTheme } = useTheme()
  const sidebarOpen = useLayoutStore((state) => state.sidebarOpen)
  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar)

  return (
    <header className="flex items-center gap-4 border-b border-border bg-surface px-4 py-3">
      <div className="flex shrink-0 items-center gap-3">
        {!sidebarOpen ? (
          <button
            type="button"
            aria-label="Show sidebar"
            onClick={toggleSidebar}
            className="rounded border border-border p-1.5 text-text-secondary transition-colors hover:border-accent/40 hover:text-text"
          >
            <SidebarToggleIcon />
          </button>
        ) : null}
        <span className="text-sm font-semibold tracking-wide">Crypto Backtester</span>
      </div>

      {onChartRoute ? (
        <div className="flex min-w-0 flex-1 items-center gap-4">
          <SymbolSearch />
          <TimeframeSelector />
          <IndicatorsBar />
        </div>
      ) : (
        <div className="flex-1" />
      )}

      <div className="flex shrink-0 items-center">
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded border border-border px-2.5 py-1 text-xs text-text-secondary transition-colors hover:text-text"
        >
          {theme === 'dark' ? 'Light' : 'Dark'}
        </button>
      </div>
    </header>
  )
}
