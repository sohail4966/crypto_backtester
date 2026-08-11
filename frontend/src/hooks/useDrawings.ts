import { useMemo } from 'react'
import { drawingsFor, useDrawingStore } from '@/stores/drawingStore'
import { useChartStore } from '@/stores/chartStore'
import type { Drawing } from '@/types/drawing'

export function useDrawings(
  symbolIdOverride?: string | null,
  timeframeOverride?: string,
): Drawing[] {
  const drawings = useDrawingStore((s) => s.drawings)
  const storeSymbolId = useChartStore((s) => s.symbol?.id)
  const storeTimeframe = useChartStore((s) => s.timeframe)
  const symbolId =
    symbolIdOverride !== undefined ? symbolIdOverride : storeSymbolId
  const timeframe =
    timeframeOverride !== undefined ? timeframeOverride : storeTimeframe

  return useMemo(() => {
    if (!symbolId) {
      return []
    }
    return drawingsFor(drawings, symbolId, timeframe)
  }, [drawings, symbolId, timeframe])
}
