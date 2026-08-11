import { useEffect, useMemo, useState } from 'react'
import {
  LineStyle,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useDrawings } from '@/hooks/useDrawings'
import { useDrawingStore } from '@/stores/drawingStore'
import type { Drawing } from '@/types/drawing'
import { formatRiskReward } from '@/utils/drawingGeometry'

function hexToRgba(hex: string, alpha: number): string {
  const raw = hex.replace('#', '')
  const full =
    raw.length === 3
      ? raw
          .split('')
          .map((c) => c + c)
          .join('')
      : raw.slice(0, 6)
  const n = Number.parseInt(full, 16)
  if (!Number.isFinite(n)) {
    return `rgba(88, 166, 255, ${alpha})`
  }
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function lineStyleFrom(style: 'solid' | 'dashed' | 'dotted'): LineStyle {
  if (style === 'dashed') {
    return LineStyle.Dashed
  }
  if (style === 'dotted') {
    return LineStyle.Dotted
  }
  return LineStyle.Solid
}

interface OverlayBox {
  id: string
  kind: 'rect' | 'text' | 'rr'
  left: number
  top: number
  width?: number
  height?: number
  color: string
  fill?: string
  text?: string
  selected: boolean
}

function measureOverlays(
  drawings: Drawing[],
  chart: NonNullable<ReturnType<typeof useChartContext>['chart']>,
  candleSeries: ISeriesApi<'Candlestick'>,
  selectedId: string | null,
): OverlayBox[] {
  const boxes: OverlayBox[] = []
  const timeScale = chart.timeScale()

  for (const drawing of drawings) {
    const selected = drawing.id === selectedId
    if (drawing.type === 'rectangle') {
      const x1 = timeScale.timeToCoordinate(drawing.topLeft.time as UTCTimestamp)
      const y1 = candleSeries.priceToCoordinate(drawing.topLeft.price)
      const x2 = timeScale.timeToCoordinate(drawing.bottomRight.time as UTCTimestamp)
      const y2 = candleSeries.priceToCoordinate(drawing.bottomRight.price)
      if (x1 == null || y1 == null || x2 == null || y2 == null) {
        continue
      }
      const left = Math.min(Number(x1), Number(x2))
      const top = Math.min(Number(y1), Number(y2))
      const width = Math.abs(Number(x2) - Number(x1))
      const height = Math.abs(Number(y2) - Number(y1))
      boxes.push({
        id: drawing.id,
        kind: 'rect',
        left,
        top,
        width,
        height,
        color: drawing.color,
        fill: hexToRgba(drawing.color, drawing.fillOpacity),
        selected,
      })
    } else if (drawing.type === 'text_note') {
      const x = timeScale.timeToCoordinate(drawing.anchorTime as UTCTimestamp)
      const y = candleSeries.priceToCoordinate(drawing.anchorPrice)
      if (x == null || y == null) {
        continue
      }
      boxes.push({
        id: drawing.id,
        kind: 'text',
        left: Number(x),
        top: Number(y),
        color: drawing.color,
        text: drawing.text,
        selected,
      })
    } else if (drawing.type === 'price_range') {
      const yEntry = candleSeries.priceToCoordinate(drawing.entryPrice)
      const yStop = candleSeries.priceToCoordinate(drawing.stopPrice)
      if (yEntry != null && yStop != null) {
        const top = Math.min(Number(yEntry), Number(yStop))
        const height = Math.abs(Number(yEntry) - Number(yStop))
        boxes.push({
          id: `${drawing.id}-zone`,
          kind: 'rect',
          left: 0,
          top,
          width: chart.timeScale().width(),
          height,
          color: drawing.color,
          fill: hexToRgba(drawing.color, 0.12),
          selected,
        })
      }
      const labelY = yEntry ?? yStop
      if (labelY != null) {
        boxes.push({
          id: `${drawing.id}-rr`,
          kind: 'rr',
          left: 8,
          top: Number(labelY) + 4,
          color: drawing.color,
          text: formatRiskReward(drawing),
          selected,
        })
      }
    }
  }
  return boxes
}

export function DrawingsLayer({
  symbolId,
  timeframe,
}: {
  symbolId?: string | null
  timeframe?: string
} = {}) {
  const { chart, candleSeries } = useChartContext()
  const drawings = useDrawings(symbolId, timeframe)
  const selectedId = useDrawingStore((s) => s.selectedId)
  const [viewportEpoch, setViewportEpoch] = useState(0)

  useEffect(() => {
    if (!chart) {
      return
    }
    const bump = () => setViewportEpoch((n) => n + 1)
    chart.timeScale().subscribeVisibleLogicalRangeChange(bump)
    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(bump)
    }
  }, [chart])

  useEffect(() => {
    if (!chart || !candleSeries) {
      return
    }

    const priceLines: IPriceLine[] = []
    const lineSeries: ISeriesApi<'Line'>[] = []

    for (const drawing of drawings) {
      const selected = drawing.id === selectedId
      if (drawing.type === 'horizontal_line') {
        const pl = candleSeries.createPriceLine({
          price: drawing.price,
          color: drawing.color,
          lineWidth: (selected ? drawing.lineWidth + 1 : drawing.lineWidth) as 1 | 2 | 3 | 4,
          lineStyle: lineStyleFrom(drawing.style),
          axisLabelVisible: true,
          title: '',
        })
        priceLines.push(pl)
      } else if (drawing.type === 'price_range') {
        for (const [price, title] of [
          [drawing.entryPrice, 'Entry'],
          [drawing.targetPrice, 'TP'],
          [drawing.stopPrice, 'SL'],
        ] as const) {
          const pl = candleSeries.createPriceLine({
            price,
            color: drawing.color,
            lineWidth: (selected ? 2 : 1) as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title,
          })
          priceLines.push(pl)
        }
      } else if (drawing.type === 'trend_line') {
        const series = chart.addLineSeries({
          color: drawing.color,
          lineWidth: (selected ? drawing.lineWidth + 1 : drawing.lineWidth) as 1 | 2 | 3 | 4,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        })
        const points =
          drawing.p1.time <= drawing.p2.time
            ? [drawing.p1, drawing.p2]
            : [drawing.p2, drawing.p1]
        series.setData(
          points.map((p) => ({
            time: p.time as UTCTimestamp,
            value: p.price,
          })),
        )
        lineSeries.push(series)
      }
    }

    return () => {
      for (const pl of priceLines) {
        try {
          candleSeries.removePriceLine(pl)
        } catch {
          /* chart may already be disposed */
        }
      }
      for (const series of lineSeries) {
        try {
          chart.removeSeries(series)
        } catch {
          /* chart may already be disposed */
        }
      }
    }
  }, [candleSeries, chart, drawings, selectedId, viewportEpoch])

  const overlays = useMemo(() => {
    if (!chart || !candleSeries) {
      return []
    }
    void viewportEpoch
    return measureOverlays(drawings, chart, candleSeries, selectedId)
  }, [candleSeries, chart, drawings, selectedId, viewportEpoch])

  if (!chart || !candleSeries) {
    return null
  }

  return (
    <div className="pointer-events-none absolute inset-0 z-[5] overflow-hidden">
      {overlays.map((box) => {
        if (box.kind === 'rect') {
          return (
            <div
              key={box.id}
              style={{
                position: 'absolute',
                left: box.left,
                top: box.top,
                width: box.width,
                height: box.height,
                background: box.fill,
                border: `${box.selected ? 2 : 1}px solid ${box.color}`,
                boxSizing: 'border-box',
              }}
            />
          )
        }
        return (
          <div
            key={box.id}
            style={{
              position: 'absolute',
              left: box.left,
              top: box.top,
              color: box.color,
              fontSize: 11,
              fontWeight: box.selected ? 600 : 500,
              padding: '2px 4px',
              background: 'rgba(13, 17, 23, 0.75)',
              borderRadius: 2,
              whiteSpace: 'nowrap',
              border: box.selected ? `1px solid ${box.color}` : '1px solid transparent',
            }}
          >
            {box.text}
          </div>
        )
      })}
    </div>
  )
}
