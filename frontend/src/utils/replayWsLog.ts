import type { ReplayServerEvent, ReplayWsCommand } from '@/types/replay'

const DEBUG =
  import.meta.env.DEV ||
  import.meta.env.VITE_REPLAY_WS_DEBUG === 'true' ||
  import.meta.env.VITE_REPLAY_WS_DEBUG === '1'

function summarizeEvent(event: ReplayServerEvent): Record<string, unknown> {
  switch (event.type) {
    case 'replay_state':
      return {
        state: event.state,
        cursor: event.cursor,
        startAnchor: event.startAnchor ?? (event as { start?: number }).start,
        latestAvailable: event.latestAvailable,
        speed: event.speed,
        queueRemaining: event.queueRemaining,
      }
    case 'snapshot':
      return {
        barCount: event.bars.length,
        cursor: event.cursor,
        startAnchor: event.startAnchor,
        latestAvailable: event.latestAvailable,
        indicatorSeries: Object.keys(event.indicators).length,
      }
    case 'tick_batch':
      return {
        tickCount: event.ticks.length,
        cursor: event.cursor,
        queueRemaining: event.queueRemaining,
        firstBar: event.ticks[0]?.bar?.time,
        lastBar: event.ticks[event.ticks.length - 1]?.bar?.time,
      }
    case 'buffer_ready':
      return {
        bufferEnd: event.bufferEnd,
        latestAvailable: event.latestAvailable,
      }
    case 'error':
      return { code: event.code, message: event.message }
    default:
      return { type: event.type }
  }
}

export function logReplayWsRecv(event: ReplayServerEvent): void {
  if (!DEBUG) {
    return
  }
  const summary = summarizeEvent(event)
  console.log(`[replay ws] ← ${event.type}`, summary)
  if (event.type === 'tick_batch' || event.type === 'snapshot' || event.type === 'error') {
    console.debug('[replay ws] full payload', event)
  }
}

export function logReplayWsSend(command: ReplayWsCommand, queued = false): void {
  if (!DEBUG) {
    return
  }
  const tag = queued ? ' (queued)' : ''
  console.log(`[replay ws] → ${command.action}${tag}`, command)
}

export function logReplayWsLifecycle(message: string, detail?: unknown): void {
  if (!DEBUG) {
    return
  }
  if (detail !== undefined) {
    console.log(`[replay ws] ${message}`, detail)
  } else {
    console.log(`[replay ws] ${message}`)
  }
}
