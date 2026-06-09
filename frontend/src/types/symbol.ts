export type SymbolAssetType = 'spot' | 'perp' | 'futures'

export interface Symbol {
  id: string
  ticker: string
  exchange: string
  baseAsset: string
  quoteAsset: string
  tickSize: number
  lotSize: number
  type: SymbolAssetType
  active: boolean
  sortOrder: number
}
