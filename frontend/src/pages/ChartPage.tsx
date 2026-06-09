import { ChartContainer } from '@/components/Chart/ChartContainer'
import { useDefaultSymbol } from '@/hooks/useDefaultSymbol'

export function ChartPage() {
  useDefaultSymbol()

  return (
    <div className="-m-6 flex h-full min-h-0 flex-1 flex-col">
      <ChartContainer className="relative h-full min-h-0 flex-1" />
    </div>
  )
}
