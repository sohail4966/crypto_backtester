import { TickMarkType, type UTCTimestamp } from 'lightweight-charts'
import { describe, expect, it } from 'vitest'
import {
  createChartTimezoneFormatters,
  formatTimezoneOffsetLabel,
  resolveChartTimeZone,
} from '@/utils/chartTimezone'

describe('chartTimezone', () => {
  it('formats UTC crosshair labels', () => {
    const { timeFormatter } = createChartTimezoneFormatters('UTC')
    const label = timeFormatter(1_704_067_200 as UTCTimestamp)
    expect(label).toContain('Jan')
    expect(label).toContain('24')
  })

  it('formats axis tick marks in the selected zone', () => {
    const { tickMarkFormatter } = createChartTimezoneFormatters('UTC')
    const label = tickMarkFormatter(1_704_067_200 as UTCTimestamp, TickMarkType.Time, 'en-US')
    expect(label).toMatch(/\d{2}:\d{2}/)
  })

  it('resolves local to a browser timezone', () => {
    expect(resolveChartTimeZone('local').length).toBeGreaterThan(0)
  })

  it('returns an offset label', () => {
    expect(formatTimezoneOffsetLabel('UTC')).toMatch(/GMT|UTC/)
  })
})
