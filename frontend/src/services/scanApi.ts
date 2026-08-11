import { apiRequest } from '@/services/api'

export type ScanRequest = {
  symbols: string[]
  timeframe: string
  start: number
  end: number
  strategy_name?: string
}

export type ScanResponse = {
  scan_id?: string
  scanId?: string
  persisted?: boolean
  results?: unknown[]
  [key: string]: unknown
}

/** Thin Phase-1 client for POST /scan (FE-006). Sends Bearer via apiRequest. */
export function runScan(body: ScanRequest): Promise<ScanResponse> {
  return apiRequest<ScanResponse>('/scan', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getScan(scanId: string): Promise<ScanResponse> {
  return apiRequest<ScanResponse>(`/scan/${encodeURIComponent(scanId)}`)
}
