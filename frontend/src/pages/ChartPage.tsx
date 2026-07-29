import { ChartContainer } from '@/components/Chart/ChartContainer'
import { IndicatorSettingsDialog } from '@/components/Indicators/IndicatorSettingsDialog'
import { useDefaultSymbol } from '@/hooks/useDefaultSymbol'
import { useIndicatorStore } from '@/stores/indicatorStore'

export function ChartPage() {
  useDefaultSymbol()
  const settingsInstanceId = useIndicatorStore((state) => state.settingsInstanceId)
  const closeSettings = useIndicatorStore((state) => state.closeSettings)

  return (
    <div className="-m-6 flex h-full min-h-0 flex-1 flex-col">
      <div className="relative min-h-0 flex-1">
        <ChartContainer className="relative h-full min-h-0 flex-1" />
      </div>

      {settingsInstanceId ? <IndicatorSettingsDialog onClose={closeSettings} /> : null}
    </div>
  )
}
