import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Theme } from '@/types/theme'
import { ThemeContext } from '@/app/ThemeContext'
import {
  readThemeBootHint,
  writeThemeBootHint,
} from '@/services/workspaceStorage'
import { useWorkspaceStore } from '@/stores/workspaceStore'

function applyThemeToDocument(theme: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = theme
  }
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const workspaceTheme = useWorkspaceStore((s) => s.theme)
  const workspaceHydrated = useWorkspaceStore((s) => s.hydrated)
  const setWorkspaceTheme = useWorkspaceStore((s) => s.setTheme)

  const [bootTheme, setBootTheme] = useState<Theme>(() => {
    const initial = readThemeBootHint()
    applyThemeToDocument(initial)
    return initial
  })

  const theme = workspaceHydrated ? workspaceTheme : bootTheme

  useEffect(() => {
    applyThemeToDocument(theme)
    writeThemeBootHint(theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    if (workspaceHydrated) {
      setWorkspaceTheme(next)
    } else {
      setBootTheme(next)
    }
  }, [setWorkspaceTheme, theme, workspaceHydrated])

  const value = useMemo(
    () => ({
      theme,
      toggleTheme,
    }),
    [theme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
