import type { ApiErrorBody, HealthResponse } from '@/types/api'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

async function parseErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return response.json() as Promise<unknown>
  }
  return response.text()
}

function formatErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') {
    return fallback
  }

  const payload = body as ApiErrorBody
  if (typeof payload.detail === 'string') {
    return payload.detail
  }
  if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg
  }
  if (typeof payload.message === 'string') {
    return payload.message
  }
  return fallback
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await parseErrorBody(response)
    throw new ApiError(
      response.status,
      formatErrorMessage(body, response.statusText),
      body,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/meta/health')
}
