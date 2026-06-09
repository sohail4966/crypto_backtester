import { useEffect } from 'react'
import { defaultSymbolId, useChartStore } from '@/stores/chartStore'
import { getSymbol, searchSymbols } from '@/services/chartDataAdapter'

/** Bootstrap a structured Symbol on first visit so chart-data can load immediately. */
export function useDefaultSymbol() {
  const symbol = useChartStore((state) => state.symbol)
  const setSymbol = useChartStore((state) => state.setSymbol)

  useEffect(() => {
    if (symbol) {
      return
    }

    let cancelled = false

    async function loadDefault() {
      try {
        const resolved = await getSymbol(defaultSymbolId)
        if (!cancelled) {
          setSymbol(resolved)
        }
        return
      } catch {
        // Dev DB may not seed BTC/USDT — search still returns a structured Symbol entity.
      }

      const results = await searchSymbols('BTC')
      if (!cancelled && results[0]) {
        setSymbol(results[0])
      }
    }

    void loadDefault()

    return () => {
      cancelled = true
    }
  }, [setSymbol, symbol])
}
