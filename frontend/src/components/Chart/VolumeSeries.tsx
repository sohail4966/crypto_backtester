import { useEffect } from 'react'
import type { Theme } from '@/types/theme'
import { useChartContext } from '@/components/Chart/ChartContext'
import { useChartStore } from '@/stores/chartStore'
import type { OHLCVBar } from '@/types/candle'
import { toUtcTimestamp } from '@/utils/chartSeriesData'
import { resolveChartColor } from '@/utils/color'

interface VolumeSeriesProps {
  candles: OHLCVBar[]
  theme: Theme
}

export function VolumeSeries({ candles, theme }: VolumeSeriesProps) {
  const { volumeSeries } = useChartContext()
  const showVolume = useChartStore((state) => state.showVolume)

  useEffect(() => {
    volumeSeries?.applyOptions({ visible: showVolume })
  }, [showVolume, volumeSeries])

  useEffect(() => {
    return () => {
      volumeSeries?.setData([])
    }
  }, [volumeSeries])

  useEffect(() => {
    if (!volumeSeries) {
      return
    }

    if (candles.length === 0) {
      volumeSeries.setData([])
      return
    }

    // Per-bar colors must be hex — lw-charts rejects CSS variables (see utils/color.ts).
    const bull = resolveChartColor('var(--color-bull)', theme)
    const bear = resolveChartColor('var(--color-bear)', theme)

    volumeSeries.setData(
      candles.flatMap((bar) => {
        const time = toUtcTimestamp(bar.time)
        return time == null
          ? []
          : [{
              time,
              value: bar.volume,
              color: bar.close >= bar.open ? bull : bear,
            }]
      }),
    )
  }, [candles, theme, volumeSeries])

  return null
}
