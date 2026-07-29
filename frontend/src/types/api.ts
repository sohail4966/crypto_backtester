export interface ApiErrorBody {
  detail?: string | { msg: string }[]
  message?: string
}
