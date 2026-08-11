export type DrawingType =
  | 'trend_line'
  | 'horizontal_line'
  | 'rectangle'
  | 'price_range'
  | 'text_note'

export interface ChartPoint {
  time: number
  price: number
}

export interface BaseDrawing {
  id: string
  type: DrawingType
  symbolId: string
  timeframe: string
  /** Resolved hex — never CSS var() */
  color: string
  visible: boolean
  createdAt: number
}

export interface TrendLineDrawing extends BaseDrawing {
  type: 'trend_line'
  p1: ChartPoint
  p2: ChartPoint
  lineWidth: number
}

export interface HorizontalLineDrawing extends BaseDrawing {
  type: 'horizontal_line'
  price: number
  lineWidth: number
  style: 'solid' | 'dashed' | 'dotted'
}

export interface RectangleDrawing extends BaseDrawing {
  type: 'rectangle'
  topLeft: ChartPoint
  bottomRight: ChartPoint
  fillOpacity: number
}

export interface PriceRangeDrawing extends BaseDrawing {
  type: 'price_range'
  entryPrice: number
  targetPrice: number
  stopPrice: number
}

export interface TextNoteDrawing extends BaseDrawing {
  type: 'text_note'
  anchorTime: number
  anchorPrice: number
  text: string
}

export type Drawing =
  | TrendLineDrawing
  | HorizontalLineDrawing
  | RectangleDrawing
  | PriceRangeDrawing
  | TextNoteDrawing

export type DrawingDraft =
  | { type: 'trend_line'; p1: ChartPoint }
  | { type: 'rectangle'; p1: ChartPoint }
  | { type: 'price_range'; entryPrice: number; targetPrice?: number }
  | null

export interface DrawingsCacheV1 {
  version: 1
  drawings: Drawing[]
  savedAt: string
}
