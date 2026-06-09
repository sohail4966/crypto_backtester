import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type Theme = 'dark' | 'light'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const STORAGE_KEY = 'cb-theme'

function readStoredTheme(): Theme {
  try {
    const stored = globalThis.localStorage?.getItem(STORAGE_KEY)
    return stored === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

function persistTheme(theme: Theme): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, theme)
  } catch {
    // Ignore quota / private-mode errors.
  }
}

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => readStoredTheme())

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    persistTheme(theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }, [])

  const value = useMemo(
    () => ({
      theme,
      toggleTheme,
    }),
    [theme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
