import { useEffect, useRef } from 'react'
import type { IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts'
import { subscribeSync } from '@/stores/syncStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { candleCloseFromLookup, safeSetCrosshairPosition } from '@/utils/crosshairSync'

interface UseMultiChartSyncArgs {
  paneId: string
  chart: IChartApi | null
  candleSeries: ISeriesApi<'Candlestick'> | null
  chartReady: boolean
  candleCloseLookup: ReadonlyMap<number, number>
}

/**
 * Applies inbound crosshair + visible-range sync from other panes (D-87).
 * Publishing is done from ChartContainer's existing chart subscriptions.
 */
export function useMultiChartSync({
  paneId,
  chart,
  candleSeries,
  chartReady,
  candleCloseLookup,
}: UseMultiChartSyncArgs): {
  beginApply: () => void
  endApply: () => void
  isApplying: () => boolean
} {
  const applyingRef = useRef(false)
  const lookupRef = useRef(candleCloseLookup)
  lookupRef.current = candleCloseLookup

  useEffect(() => {
    if (!chart || !chartReady) {
      return
    }

    return subscribeSync((event) => {
      if (event.sourcePaneId === paneId) {
        return
      }
      const sync = useWorkspaceStore.getState().sync

      if (event.type === 'crosshair') {
        if (!sync.crosshair) {
          return
        }
        applyingRef.current = true
        try {
          if (event.time == null) {
            chart.clearCrosshairPosition()
            return
          }
          if (!candleSeries) {
            return
          }
          const close = candleCloseFromLookup(lookupRef.current, event.time)
          if (close != null) {
            safeSetCrosshairPosition(
              chart,
              close,
              event.time as UTCTimestamp,
              candleSeries,
            )
          }
        } finally {
          applyingRef.current = false
        }
        return
      }

      if (event.type === 'visibleRange') {
        if (!sync.visibleRange) {
          return
        }
        // FE-013: only apply range sync across panes that share a symbol
        // (unless symbol sync is also on — then all panes share the same symbol anyway).
        if (!sync.symbol) {
          const workspace = useWorkspaceStore.getState()
          const layout =
            workspace.layouts.find((l) => l.id === workspace.activeLayoutId) ??
            workspace.layouts[0]
          const source = layout?.panes.find((p) => p.id === event.sourcePaneId)
          const target = layout?.panes.find((p) => p.id === paneId)
          const sourceSymbol = source?.symbol?.id
          const targetSymbol = target?.symbol?.id
          if (
            sourceSymbol &&
            targetSymbol &&
            sourceSymbol !== targetSymbol
          ) {
            return
          }
        }
        applyingRef.current = true
        try {
          if (event.range == null) {
            return
          }
          chart.timeScale().setVisibleLogicalRange({
            from: event.range.from,
            to: event.range.to,
          })
        } catch {
          // Range may be invalid for a shorter series.
        } finally {
          applyingRef.current = false
        }
      }
    })
  }, [candleSeries, chart, chartReady, paneId])

  return {
    beginApply: () => {
      applyingRef.current = true
    },
    endApply: () => {
      applyingRef.current = false
    },
    isApplying: () => applyingRef.current,
  }
}
