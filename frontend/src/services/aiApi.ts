import { apiRequest } from '@/services/api'

export type AiTranslateRequest = {
  text: string
}

export type AiClarifyRequest = {
  message: string
  session_id?: string
}

export type AiExplainRequest = {
  run_id?: string
  context?: string
}

/** Thin AI HTTP clients (FE-006). Auth via Bearer once BE-004 gates /ai/*. */
export function aiTranslate(body: AiTranslateRequest): Promise<unknown> {
  return apiRequest('/ai/translate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function aiClarify(body: AiClarifyRequest): Promise<unknown> {
  return apiRequest('/ai/clarify', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function aiExplain(body: AiExplainRequest): Promise<unknown> {
  return apiRequest('/ai/explain', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
