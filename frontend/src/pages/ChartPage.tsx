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
      <ChartContainer className="relative h-full min-h-0 flex-1" />
      {settingsInstanceId ? <IndicatorSettingsDialog onClose={closeSettings} /> : null}
    </div>
  )
}
