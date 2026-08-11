import type { ApiErrorBody } from '@/types/api'
import { getAuthToken } from '@/services/authToken'
import { notifyAuthFailure } from '@/services/authSession'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

/** Paths that authenticate — do not clear session on their 401/403 responses. */
const AUTH_EXEMPT_PREFIXES = ['/auth/login', '/auth/register']

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown
  readonly code: string | null

  constructor(status: number, message: string, body?: unknown, code: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
    this.code = code
  }
}

async function parseErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return response.json() as Promise<unknown>
  }
  return response.text()
}

export function extractErrorCode(body: unknown): string | null {
  if (!body || typeof body !== 'object') {
    return null
  }
  const payload = body as ApiErrorBody
  return typeof payload.error?.code === 'string' ? payload.error.code : null
}

export function formatErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') {
    if (typeof body === 'string' && body.trim()) {
      return body
    }
    return fallback
  }

  const payload = body as ApiErrorBody
  if (typeof payload.error?.message === 'string' && payload.error.message.trim()) {
    return payload.error.message
  }
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

function shouldClearAuthOnFailure(path: string, hadToken: boolean): boolean {
  if (!hadToken) {
    return false
  }
  return !AUTH_EXEMPT_PREFIXES.some((prefix) => path.startsWith(prefix))
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getAuthToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await parseErrorBody(response)
    const code = extractErrorCode(body)
    if (
      (response.status === 401 || response.status === 403) &&
      shouldClearAuthOnFailure(path, Boolean(token))
    ) {
      notifyAuthFailure(code)
    }
    throw new ApiError(
      response.status,
      formatErrorMessage(body, response.statusText),
      body,
      code,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
