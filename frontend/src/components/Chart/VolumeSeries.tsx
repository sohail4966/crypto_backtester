import { useEffect } from 'react'
import type { UTCTimestamp } from 'lightweight-charts'
import type { Theme } from '@/types/theme'
import { useChartContext } from '@/components/Chart/ChartContext'
import type { OHLCVBar } from '@/types/candle'
import { resolveChartColor } from '@/utils/color'

interface VolumeSeriesProps {
  candles: OHLCVBar[]
  theme: Theme
}

export function VolumeSeries({ candles, theme }: VolumeSeriesProps) {
  const { volumeSeries } = useChartContext()

  useEffect(() => {
    if (!volumeSeries) {
      return
    }

    // Per-bar colors must be hex — lw-charts rejects CSS variables (see utils/color.ts).
    const bull = resolveChartColor('var(--color-bull)', theme)
    const bear = resolveChartColor('var(--color-bear)', theme)

    volumeSeries.setData(
      candles.map((bar) => ({
        time: bar.time as UTCTimestamp,
        value: bar.volume,
        color: bar.close >= bar.open ? bull : bear,
      })),
    )
  }, [candles, theme, volumeSeries])

  return null
}
