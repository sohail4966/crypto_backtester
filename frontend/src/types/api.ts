export interface HealthResponse {
  status: string
  version: string
  database: 'ok' | 'error'
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[]
  message?: string
}
