export interface ApiErrorEnvelope {
  code?: string
  message?: string
}

export interface ApiErrorBody {
  error?: ApiErrorEnvelope
  detail?: string | { msg: string }[]
  message?: string
}
