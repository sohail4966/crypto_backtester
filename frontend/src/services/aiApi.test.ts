import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

import { apiRequest } from '@/services/api'
import {
  aiClarify,
  aiExplain,
  aiTranslate,
  type AiTranslateResponse,
} from '@/services/aiApi'

const mockedApi = vi.mocked(apiRequest)

describe('aiApi', () => {
  beforeEach(() => {
    mockedApi.mockReset()
  })

  it('aiTranslate POSTs { text } and narrows on the discriminated status', async () => {
    const ok: AiTranslateResponse = {
      status: 'ok',
      strategy: { indicator: 'rsi' },
      explanation: 'Buy the dip',
    }
    mockedApi.mockResolvedValueOnce(ok)
    const result = await aiTranslate({ text: 'when rsi is oversold buy' })
    expect(mockedApi).toHaveBeenCalledWith('/ai/translate', {
      method: 'POST',
      body: JSON.stringify({ text: 'when rsi is oversold buy' }),
    })
    if (result.status === 'ok') {
      expect(result.strategy).toEqual({ indicator: 'rsi' })
      expect(result.explanation).toBe('Buy the dip')
    } else {
      throw new Error('expected ok response')
    }
  })

  it('aiClarify POSTs { session_id, answers } and can return either union arm', async () => {
    const clarify: AiTranslateResponse = {
      status: 'needs_clarification',
      session_id: 'sess-1',
      questions: [{ id: 'q1', prompt: 'Which side?', options: ['long', 'short'] }],
    }
    mockedApi.mockResolvedValueOnce(clarify)
    const body = { session_id: 'sess-1', answers: { q1: 'long' } }
    const result = await aiClarify(body)
    expect(mockedApi).toHaveBeenCalledWith('/ai/clarify', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    if (result.status === 'needs_clarification') {
      expect(result.session_id).toBe('sess-1')
      expect(result.questions[0]?.options).toEqual(['long', 'short'])
    } else {
      throw new Error('expected needs_clarification')
    }
  })

  it('aiExplain POSTs { strategy } and returns { explanation }', async () => {
    mockedApi.mockResolvedValueOnce({ explanation: 'RSI-driven mean reversion' })
    const body = { strategy: { indicator: 'rsi', period: 14 } }
    const result = await aiExplain(body)
    expect(mockedApi).toHaveBeenCalledWith('/ai/explain', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    expect(result.explanation).toBe('RSI-driven mean reversion')
  })
})
