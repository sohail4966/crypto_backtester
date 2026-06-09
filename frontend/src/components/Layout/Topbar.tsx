import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'
import { useTheme } from '@/app/ThemeProvider'
import { getHealth } from '@/services/api'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded px-3 py-1.5 text-sm font-medium transition-colors',
    isActive
      ? 'bg-accent/15 text-accent'
      : 'text-text-secondary hover:bg-surface hover:text-text',
  ].join(' ')

export function Topbar() {
  const { theme, toggleTheme } = useTheme()
  const healthQuery = useQuery({
    queryKey: ['meta', 'health'],
    queryFn: getHealth,
  })

  const healthLabel = (() => {
    if (healthQuery.isPending) return 'API: checking…'
    if (healthQuery.isError) return 'API: unreachable'
    const { status, version, database } = healthQuery.data
    return `API: ${status} v${version} · DB ${database}`
  })()

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

      <div className="flex items-center gap-3">
        <span
          className="hidden text-xs text-text-secondary sm:inline"
          title={healthQuery.isError ? String(healthQuery.error) : undefined}
        >
          {healthLabel}
        </span>
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
