import { useCallback, useEffect, useRef, type ReactNode } from 'react'
import { WORKSPACE_PERSIST_DEBOUNCE_MS } from '@/constants/workspace'
import { useWorkspaceKeyboard } from '@/hooks/useWorkspaceKeyboard'
import { useToast } from '@/components/ui/Toast'
import {
  createDefaultWorkspace,
  readWorkspaceCache,
  writeThemeBootHint,
  writeWorkspaceCache,
} from '@/services/workspaceStorage'
import { registerChartWorkspaceBridge, useChartStore } from '@/stores/chartStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import type { ChartTimeframe } from '@/constants/chart'
import type { Symbol } from '@/types/symbol'

interface WorkspaceRootProps {
  children: ReactNode
}

export function WorkspaceRoot({ children }: WorkspaceRootProps) {
  const { showToast } = useToast()
  const hydrated = useWorkspaceStore((s) => s.hydrated)
  const theme = useWorkspaceStore((s) => s.theme)
  const layouts = useWorkspaceStore((s) => s.layouts)
  const activeLayoutId = useWorkspaceStore((s) => s.activeLayoutId)
  const activePaneId = useWorkspaceStore((s) => s.activePaneId)
  const sync = useWorkspaceStore((s) => s.sync)
  const persistGeneration = useRef(0)

  const flushPersist = useCallback(async () => {
    const payload = useWorkspaceStore.getState().toPersistPayload()
    await writeWorkspaceCache(payload)
  }, [])

  const handleSave = useCallback(() => {
    void flushPersist()
      .then(() => {
        showToast('Workspace saved')
      })
      .catch(() => {
        showToast('Workspace save failed')
      })
  }, [flushPersist, showToast])

  useWorkspaceKeyboard({ onSave: handleSave })

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const cache = (await readWorkspaceCache()) ?? createDefaultWorkspace()
        if (cancelled) {
          return
        }
        useWorkspaceStore.getState().hydrate(cache)
        writeThemeBootHint(cache.theme)

        const layout =
          cache.layouts.find((item) => item.id === cache.activeLayoutId) ??
          cache.layouts[0]
        const pane =
          layout?.panes.find((item) => item.id === cache.activePaneId) ??
          layout?.panes[0]
        if (pane) {
          useChartStore.getState().applyPaneState(pane.symbol, pane.timeframe)
        }
      } catch {
        if (!cancelled) {
          const fallback = createDefaultWorkspace()
          useWorkspaceStore.getState().hydrate(fallback)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    registerChartWorkspaceBridge({
      onSymbol: (symbol: Symbol) => {
        useWorkspaceStore.getState().updateActivePaneSymbol(symbol)
      },
      onTimeframe: (timeframe: ChartTimeframe) => {
        useWorkspaceStore.getState().updateActivePaneTimeframe(timeframe)
      },
    })
    return () => {
      registerChartWorkspaceBridge({})
    }
  }, [])

  // When active pane changes, mirror into chartStore without write-back loop.
  useEffect(() => {
    if (!hydrated) {
      return
    }
    const pane = useWorkspaceStore.getState().getActivePane()
    if (!pane) {
      return
    }
    const chart = useChartStore.getState()
    if (
      chart.symbol?.id === pane.symbol?.id &&
      chart.timeframe === pane.timeframe
    ) {
      return
    }
    useChartStore.getState().applyPaneState(pane.symbol, pane.timeframe)
  }, [activePaneId, hydrated])

  useEffect(() => {
    if (!hydrated) {
      return
    }
    writeThemeBootHint(theme)
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = theme
    }
  }, [hydrated, theme])

  useEffect(() => {
    if (!hydrated) {
      return
    }
    const generation = ++persistGeneration.current
    const timer = window.setTimeout(() => {
      if (generation !== persistGeneration.current) {
        return
      }
      void flushPersist().catch(() => {
        /* persistence errors are non-fatal */
      })
    }, WORKSPACE_PERSIST_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [
    activeLayoutId,
    activePaneId,
    flushPersist,
    hydrated,
    layouts,
    sync,
    theme,
  ])

  return children
}
