import { describe, expect, it } from 'vitest'
import { parseReplayWsMessage } from '@/utils/replayWsParse'

describe('parseReplayWsMessage', () => {
  it('parses standard JSON', () => {
    expect(parseReplayWsMessage('{"type":"replay_state","state":"paused"}')).toEqual({
      type: 'replay_state',
      state: 'paused',
    })
  })

  it('sanitizes Python NaN literals in tick_batch payloads', () => {
    const raw =
      '{"type":"tick_batch","ticks":[{"bar":{"time":1},"indicators":{"rsi":{"time":1,"value":NaN}}}],"cursor":1,"queueRemaining":0}'
    const parsed = parseReplayWsMessage(raw) as {
      ticks: Array<{ indicators: { rsi: { value: null } } }>
    }
    expect(parsed.ticks[0].indicators.rsi.value).toBeNull()
  })
})
