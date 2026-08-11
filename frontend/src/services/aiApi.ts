import { apiRequest } from '@/services/api'

/**
 * Thin HTTP clients for POST /ai/translate|clarify|explain (FE-L2-006).
 *
 * Request/response shapes mirror the BE Pydantic models exactly
 * (``backend/api/schemas/ai.py``). Auth via Bearer flows through ``apiRequest``.
 */

export interface AiTranslateRequest {
  text: string
}

export interface AiClarifyRequest {
  session_id: string
  answers: Record<string, string>
}

export interface AiExplainRequest {
  strategy: Record<string, unknown>
}

export interface ClarificationQuestion {
  id: string
  prompt: string
  options: string[]
}

export type AiTranslateResponse =
  | {
      status: 'ok'
      strategy: Record<string, unknown>
      explanation: string
    }
  | {
      status: 'needs_clarification'
      session_id: string
      questions: ClarificationQuestion[]
    }

export interface AiExplainResponse {
  explanation: string
}

export function aiTranslate(body: AiTranslateRequest): Promise<AiTranslateResponse> {
  return apiRequest<AiTranslateResponse>('/ai/translate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** Same discriminated union as ``translate`` — BE may return either shape. */
export function aiClarify(body: AiClarifyRequest): Promise<AiTranslateResponse> {
  return apiRequest<AiTranslateResponse>('/ai/clarify', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function aiExplain(body: AiExplainRequest): Promise<AiExplainResponse> {
  return apiRequest<AiExplainResponse>('/ai/explain', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
