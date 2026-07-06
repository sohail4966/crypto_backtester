import type { Theme } from '@/types/theme'

/**
 * lightweight-charts cannot parse CSS `var(--token)`.
 * Chart code always passes an explicit theme — palettes are the single source of truth.
 */
const THEME_PALETTES: Record<Theme, Record<string, string>> = {
  dark: {
    '--color-bg': '#0d1117',
    '--color-surface': '#161b22',
    '--color-border': '#30363d',
    '--color-text': '#e6edf3',
    '--color-text-secondary': '#8b949e',
    '--color-accent': '#58a6ff',
    '--color-bull': '#3fb950',
    '--color-bear': '#f85149',
  },
  light: {
    '--color-bg': '#ffffff',
    '--color-surface': '#f6f8fa',
    '--color-border': '#d0d7de',
    '--color-text': '#1f2328',
    '--color-text-secondary': '#656d76',
    '--color-accent': '#0969da',
    '--color-bull': '#1a7f37',
    '--color-bear': '#cf222e',
  },
}

export function resolveChartColor(value: string, theme: Theme): string {
  const trimmed = value.trim()
  const match = /^var\((--[^)]+)\)$/.exec(trimmed)
  if (!match) {
    return trimmed
  }
  return THEME_PALETTES[theme][match[1]] ?? '#888888'
}

/** Apply alpha to a resolved hex chart color for dimmed replay context bars. */
export function resolveChartColorWithOpacity(
  value: string,
  theme: Theme,
  opacity: number,
): string {
  const hex = resolveChartColor(value, theme)
  const normalized = hex.replace('#', '')
  if (normalized.length !== 6) {
    return hex
  }
  const r = Number.parseInt(normalized.slice(0, 2), 16)
  const g = Number.parseInt(normalized.slice(2, 4), 16)
  const b = Number.parseInt(normalized.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}
