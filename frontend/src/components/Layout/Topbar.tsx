import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '@/hooks/useTheme'
import { ChartSettingsMenu } from '@/components/Layout/ChartSettingsMenu'
import { TimeframeSelector } from '@/components/Layout/TimeframeSelector'
import { TimezoneSelector } from '@/components/Layout/TimezoneSelector'
import { SymbolSearch } from '@/components/Watchlist/SymbolSearch'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded px-3 py-1.5 text-sm font-medium transition-colors',
    isActive
      ? 'bg-accent/15 text-accent'
      : 'text-text-secondary hover:bg-surface hover:text-text',
  ].join(' ')

export function Topbar() {
  const location = useLocation()
  const onChartRoute = location.pathname === '/'
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-6">
        <span className="text-sm font-semibold tracking-wide">Crypto Backtester</span>
        <nav className="flex items-center gap-1">
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
      </div>

      {onChartRoute ? (
        <div className="hidden flex-1 items-center justify-center gap-4 px-4 lg:flex">
          <SymbolSearch />
          <TimeframeSelector />
          <TimezoneSelector />
          <ChartSettingsMenu />
        </div>
      ) : null}

      <div className="flex items-center gap-3">
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
