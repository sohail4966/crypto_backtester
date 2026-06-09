import { TickMarkType, type Time } from 'lightweight-charts'
import {
  CHART_TIMEZONE_OPTIONS,
  CHART_TIMEZONE_STORAGE_KEY,
  DEFAULT_CHART_TIMEZONE,
  type ChartTimezoneId,
} from '@/constants/timezone'

function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}

export function resolveChartTimeZone(id: ChartTimezoneId): string {
  return id === 'local' ? browserTimeZone() : id
}

export function loadChartTimezonePreference(): ChartTimezoneId {
  const stored = localStorage.getItem(CHART_TIMEZONE_STORAGE_KEY)
  if (stored && CHART_TIMEZONE_OPTIONS.some((option) => option.id === stored)) {
    return stored as ChartTimezoneId
  }
  return DEFAULT_CHART_TIMEZONE
}

export function saveChartTimezonePreference(id: ChartTimezoneId): void {
  localStorage.setItem(CHART_TIMEZONE_STORAGE_KEY, id)
}

function utcSeconds(time: Time): number | null {
  return typeof time === 'number' ? time : null
}

function formatInZone(
  timestamp: number,
  timeZone: string,
  options: Intl.DateTimeFormatOptions,
): string {
  return new Intl.DateTimeFormat('en-US', { ...options, timeZone }).format(
    new Date(timestamp * 1000),
  )
}

export function createChartTimezoneFormatters(timeZone: string) {
  const timeFormatter = (time: Time) => {
    const ts = utcSeconds(time)
    if (ts == null) {
      return String(time)
    }

    return formatInZone(ts, timeZone, {
      month: 'short',
      day: 'numeric',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  }

  const tickMarkFormatter = (
    time: Time,
    tickMarkType: TickMarkType,
    _locale: string,
  ) => {
    const ts = utcSeconds(time)
    if (ts == null) {
      return null
    }

    switch (tickMarkType) {
      case TickMarkType.Year:
        return formatInZone(ts, timeZone, { year: '2-digit' })
      case TickMarkType.Month:
        return formatInZone(ts, timeZone, { month: 'short' })
      case TickMarkType.DayOfMonth:
        return formatInZone(ts, timeZone, { day: 'numeric', month: 'short' })
      case TickMarkType.Time:
      case TickMarkType.TimeWithSeconds:
        return formatInZone(ts, timeZone, {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        })
      default:
        return null
    }
  }

  return { timeFormatter, tickMarkFormatter }
}

/** Short offset label for the selector, e.g. "UTC+5:30". */
export function formatTimezoneOffsetLabel(timeZone: string, date = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    timeZoneName: 'shortOffset',
  }).formatToParts(date)
  const offset = parts.find((part) => part.type === 'timeZoneName')?.value
  return offset ?? timeZone
}
