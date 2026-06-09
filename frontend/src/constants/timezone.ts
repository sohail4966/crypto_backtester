export const CHART_TIMEZONE_STORAGE_KEY = 'chart-timezone'

/** `local` resolves to the browser IANA zone at runtime. */
export const CHART_TIMEZONE_OPTIONS = [
  { id: 'local', label: 'Local' },
  { id: 'UTC', label: 'UTC' },
  { id: 'America/New_York', label: 'New York' },
  { id: 'Europe/London', label: 'London' },
  { id: 'Europe/Berlin', label: 'Berlin' },
  { id: 'Asia/Dubai', label: 'Dubai' },
  { id: 'Asia/Kolkata', label: 'Kolkata' },
  { id: 'Asia/Singapore', label: 'Singapore' },
  { id: 'Asia/Tokyo', label: 'Tokyo' },
] as const

export type ChartTimezoneId = (typeof CHART_TIMEZONE_OPTIONS)[number]['id']

export const DEFAULT_CHART_TIMEZONE: ChartTimezoneId = 'local'
