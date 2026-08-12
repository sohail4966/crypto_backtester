import { apiRequest } from '@/services/api'
import { USER_ID_STORAGE_KEY } from '@/constants/watchlist'

/**
 * Thin HTTP client for POST/GET /scan (FE-L2-005).
 *
 * Shapes mirror the BE Pydantic models exactly:
 *   - Request:  ``ScanCreateRequest`` (``backend/api/schemas/scan.py``)
 *   - Response: ``ScanRunResponse``
 *
 * The BE keeps snake_case on the wire; the FE preserves it verbatim to avoid
 * an extra normalize layer.
 */

export type ScanAlertTrigger = 'edge' | 'level'

export interface ScanCreateRequest {
  /** ≥ 1 timeframe strings. */
  timeframes: string[]
  start: number
  end: number
  /** Opaque strategy DSL blob (same shape produced by ``POST /ai/translate``). */
  condition: Record<string, unknown>
  /** Optional symbol allowlist; when omitted the BE scans the full catalog. */
  symbols?: string[]
  /** Defaults to ``'edge'`` server-side. */
  alert_trigger?: ScanAlertTrigger
  /** Defaults to ``true`` server-side. */
  persist?: boolean
}

export interface ScanMatch {
  symbol: string
  timeframe: string
  bar_ts: string
  triggered: boolean
  close: number | null
}

export interface ScanError {
  symbol: string
  timeframe: string
  error: string
}

export interface ScanRunResponse {
  /** ``null`` when ``persist=false``. */
  scan_id: string | null
  timeframes: string[]
  symbols: string[]
  start: number
  end: number
  alert_trigger: ScanAlertTrigger
  matches: ScanMatch[]
  alert_count: number
  duration_ms: number
  scanned_pairs: number
  errors: ScanError[]
  persisted: boolean
}

export function runScan(body: ScanCreateRequest): Promise<ScanRunResponse> {
  return apiRequest<ScanRunResponse>('/scan', {
    method: 'POST',
    body: JSON.stringify({
      ...body,
      user_id: localStorage.getItem(USER_ID_STORAGE_KEY) ?? undefined,
    }),
  })
}

export function getScan(scanId: string): Promise<ScanRunResponse> {
  return apiRequest<ScanRunResponse>(`/scan/${encodeURIComponent(scanId)}`)
}
