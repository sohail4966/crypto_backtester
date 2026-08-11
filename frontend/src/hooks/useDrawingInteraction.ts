import { useEffect, useRef } from 'react'
import type { IChartApi, ISeriesApi, MouseEventParams } from 'lightweight-charts'
import {
  DEFAULT_HORIZONTAL_LINE_WIDTH,
  DEFAULT_RECT_FILL_OPACITY,
  DEFAULT_TREND_LINE_WIDTH,
} from '@/constants/drawings'
import { useTheme } from '@/hooks/useTheme'
import { useChartStore } from '@/stores/chartStore'
import { createDrawingId, drawingsFor, useDrawingStore } from '@/stores/drawingStore'
import { useReplayStore } from '@/stores/replayStore'
import type { ChartPoint, Drawing } from '@/types/drawing'
import type { Theme } from '@/types/theme'
import { findHitDrawing, normalizeRectangleCorners } from '@/utils/drawingGeometry'
import { resolveChartColor } from '@/utils/color'

interface UseDrawingInteractionOptions {
  chart: IChartApi | null
  candleSeries: ISeriesApi<'Candlestick'> | null
  chartReady: boolean
  /** Pane-scoped identity (FE-015); falls back to chartStore when omitted. */
  symbolId?: string | null
  timeframe?: string
}

function resolveClickPoint(
  param: MouseEventParams,
  candleSeries: ISeriesApi<'Candlestick'>,
): ChartPoint | null {
  if (!param.point || param.time === undefined) {
    return null
  }
  const price = candleSeries.coordinateToPrice(param.point.y)
  if (price == null || !Number.isFinite(Number(price))) {
    return null
  }
  const time = Number(param.time)
  if (!Number.isFinite(time)) {
    return null
  }
  return { time, price: Number(price) }
}

function defaultColor(theme: Theme): string {
  return resolveChartColor('var(--color-accent)', theme)
}

export function useDrawingInteraction({
  chart,
  candleSeries,
  chartReady,
  symbolId: symbolIdProp,
  timeframe: timeframeProp,
}: UseDrawingInteractionOptions): void {
  const { theme } = useTheme()
  const themeRef = useRef(theme)
  themeRef.current = theme
  const symbolIdRef = useRef(symbolIdProp)
  const timeframeRef = useRef(timeframeProp)
  symbolIdRef.current = symbolIdProp
  timeframeRef.current = timeframeProp

  useEffect(() => {
    if (!chart || !candleSeries || !chartReady) {
      return
    }

    const handler = (param: MouseEventParams) => {
      if (useReplayStore.getState().phase === 'pick_anchor') {
        return
      }

      const store = useDrawingStore.getState()
      const symbolId =
        symbolIdRef.current ?? useChartStore.getState().symbol?.id ?? null
      const timeframe =
        timeframeRef.current ?? useChartStore.getState().timeframe
      if (!symbolId) {
        return
      }

      const point = resolveClickPoint(param, candleSeries)
      if (!point) {
        return
      }

      const tool = store.activeTool
      const draft = store.draft
      const color = defaultColor(themeRef.current)

      if (tool == null && draft == null) {
        const visible = drawingsFor(store.drawings, symbolId, timeframe)
        const hit = findHitDrawing(visible, {
          x: param.point!.x,
          y: param.point!.y,
          timeToX: (time) => {
            const c = chart.timeScale().timeToCoordinate(time as never)
            return c == null ? null : Number(c)
          },
          priceToY: (price) => {
            const c = candleSeries.priceToCoordinate(price)
            return c == null ? null : Number(c)
          },
        })
        store.setSelectedId(hit?.id ?? null)
        return
      }

      if (tool === 'horizontal_line') {
        const drawing: Drawing = {
          id: createDrawingId(),
          type: 'horizontal_line',
          symbolId,
          timeframe,
          color,
          visible: true,
          createdAt: Date.now(),
          price: point.price,
          lineWidth: DEFAULT_HORIZONTAL_LINE_WIDTH,
          style: 'solid',
        }
        store.addDrawing(drawing)
        return
      }

      if (tool === 'text_note') {
        const text = window.prompt('Text note')
        if (text == null || text.trim() === '') {
          store.clearTool()
          return
        }
        const drawing: Drawing = {
          id: createDrawingId(),
          type: 'text_note',
          symbolId,
          timeframe,
          color,
          visible: true,
          createdAt: Date.now(),
          anchorTime: point.time,
          anchorPrice: point.price,
          text: text.trim(),
        }
        store.addDrawing(drawing)
        return
      }

      if (tool === 'trend_line') {
        if (draft?.type !== 'trend_line') {
          store.setDraft({ type: 'trend_line', p1: point })
          return
        }
        const [p1, p2] =
          draft.p1.time <= point.time
            ? [draft.p1, point]
            : [point, draft.p1]
        const drawing: Drawing = {
          id: createDrawingId(),
          type: 'trend_line',
          symbolId,
          timeframe,
          color,
          visible: true,
          createdAt: Date.now(),
          p1,
          p2,
          lineWidth: DEFAULT_TREND_LINE_WIDTH,
        }
        store.addDrawing(drawing)
        return
      }

      if (tool === 'rectangle') {
        if (draft?.type !== 'rectangle') {
          store.setDraft({ type: 'rectangle', p1: point })
          return
        }
        const corners = normalizeRectangleCorners(draft.p1, point)
        const drawing: Drawing = {
          id: createDrawingId(),
          type: 'rectangle',
          symbolId,
          timeframe,
          color,
          visible: true,
          createdAt: Date.now(),
          topLeft: corners.topLeft,
          bottomRight: corners.bottomRight,
          fillOpacity: DEFAULT_RECT_FILL_OPACITY,
        }
        store.addDrawing(drawing)
        return
      }

      if (tool === 'price_range') {
        if (draft?.type !== 'price_range') {
          store.setDraft({ type: 'price_range', entryPrice: point.price })
          return
        }
        if (draft.targetPrice == null) {
          store.setDraft({
            type: 'price_range',
            entryPrice: draft.entryPrice,
            targetPrice: point.price,
          })
          return
        }
        const drawing: Drawing = {
          id: createDrawingId(),
          type: 'price_range',
          symbolId,
          timeframe,
          color,
          visible: true,
          createdAt: Date.now(),
          entryPrice: draft.entryPrice,
          targetPrice: draft.targetPrice,
          stopPrice: point.price,
        }
        store.addDrawing(drawing)
      }
    }

    chart.subscribeClick(handler)
    return () => {
      chart.unsubscribeClick(handler)
    }
  }, [candleSeries, chart, chartReady])
}
