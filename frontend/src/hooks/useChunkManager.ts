import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { LogicalRange } from 'lightweight-charts'
import {
  CHUNK_SIZE_BARS,
  LOOKBACK_CHUNKS,
  PREFETCH_THRESHOLD,
} from '@/constants/chart'
import { initialChartDataQueryKey } from '@/hooks/useChartData'
import {
  fetchChartData,
  resolveCandleDataRange,
} from '@/services/chartDataAdapter'
import { ChunkManager } from '@/services/chunkManager'
import type { CandleDataRange, OHLCVBar } from '@/types/candle'
import type { IndicatorSeriesMap, IndicatorSpec } from '@/types/indicator'
import { specsCacheKey } from '@/utils/indicatorId'
import { chartWindowFromDataRange, shiftUnixByBars, timeframeSeconds } from '@/utils/time'

type ChunkStatus = 'idle' | 'loading' | 'ready' | 'error'

interface UseChunkManagerResult {
  candles: OHLCVBar[]
  indicators: IndicatorSeriesMap
  status: ChunkStatus
  error: Error | null
  onVisibleRangeChange: (range: LogicalRange | null) => void
}

export function useChunkManager(
  symbolId: string | undefined,
  timeframe: string,
  indicatorSpecs: IndicatorSpec[],
): UseChunkManagerResult {
  const queryClient = useQueryClient()
  const managerRef = useRef(new ChunkManager())
  const generationRef = useRef(0)
  const dataRangeRef = useRef<CandleDataRange | null>(null)
  const prefetchingRef = useRef(false)
  const candlesRef = useRef<OHLCVBar[]>([])
  const indicatorsRef = useRef<IndicatorSeriesMap>({})
  const lastVisibleFromRef = useRef<number | null>(null)
  const indicatorSpecsKey = specsCacheKey(indicatorSpecs)
  const indicatorSpecsRef = useRef(indicatorSpecs)

  const [candles, setCandles] = useState<OHLCVBar[]>([])
  const [indicators, setIndicators] = useState<IndicatorSeriesMap>({})
  const [status, setStatus] = useState<ChunkStatus>('idle')
  const [error, setError] = useState<Error | null>(null)

  const syncAssembled = useCallback(() => {
    const nextCandles = managerRef.current.getAssembledCandles()
    const nextIndicators = managerRef.current.getAssembledIndicators()
    candlesRef.current = nextCandles
    indicatorsRef.current = nextIndicators
    setCandles(nextCandles)
    setIndicators(nextIndicators)
  }, [])

  useEffect(() => {
    indicatorSpecsRef.current = indicatorSpecs
  }, [indicatorSpecs, indicatorSpecsKey])

  useEffect(() => {
    if (!symbolId) {
      managerRef.current.reset()
      candlesRef.current = []
      indicatorsRef.current = {}
      setCandles([])
      setIndicators({})
      setStatus('idle')
      setError(null)
      return
    }

    const generation = ++generationRef.current
    managerRef.current.reset()
    prefetchingRef.current = false
    lastVisibleFromRef.current = null
    setStatus('loading')
    setError(null)

    async function loadInitial() {
      try {
        const range = await queryClient.ensureQueryData({
          queryKey: ['candle-data-range', symbolId, timeframe],
          queryFn: () => resolveCandleDataRange(symbolId!, timeframe),
          staleTime: 60_000,
        })

        if (generation !== generationRef.current) return

        dataRangeRef.current = range
        const window = chartWindowFromDataRange(range, CHUNK_SIZE_BARS, timeframe)

        if (!window) {
          syncAssembled()
          setStatus('ready')
          return
        }

        const request = {
          symbolId: symbolId!,
          timeframe,
          start: window.start,
          end: window.end,
          limit: CHUNK_SIZE_BARS,
          indicators: indicatorSpecsRef.current,
        }

        const data = await queryClient.ensureQueryData({
          queryKey: initialChartDataQueryKey(symbolId!, timeframe, indicatorSpecsRef.current),
          queryFn: () => fetchChartData(request),
          staleTime: 60_000,
        })

        if (generation !== generationRef.current) return

        if (data.candles.length === 0) {
          syncAssembled()
          setStatus('ready')
          return
        }

        managerRef.current.addChunk(data.start, {
          candles: data.candles,
          indicators: data.indicators,
        })

        if (range.latest != null) {
          dataRangeRef.current = {
            ...range,
            earliest: range.earliest ?? data.candles[0].time,
            latest: range.latest ?? data.candles[data.candles.length - 1].time,
            barCount: Math.max(range.barCount, data.candles.length),
          }
        }

        syncAssembled()
        setStatus('ready')
      } catch (cause) {
        if (generation !== generationRef.current) return
        setError(cause instanceof Error ? cause : new Error(String(cause)))
        setStatus('error')
      }
    }

    void loadInitial()
  }, [indicatorSpecsKey, queryClient, symbolId, syncAssembled, timeframe])

  const prefetchPriorChunk = useCallback(async () => {
    if (!symbolId || prefetchingRef.current) {
      return
    }

    const assembled = candlesRef.current
    const earliestTime = assembled[0]?.time
    const dataRange = dataRangeRef.current
    if (!earliestTime) {
      return
    }

    const barSeconds = timeframeSeconds(timeframe)
    const priorEnd = earliestTime - barSeconds
    let priorStart = shiftUnixByBars(priorEnd, timeframe, CHUNK_SIZE_BARS - 1)

    if (dataRange?.earliest != null) {
      if (earliestTime <= dataRange.earliest) {
        return
      }
      priorStart = Math.max(priorStart, dataRange.earliest)
    }

    if (managerRef.current.hasChunk(priorStart)) {
      return
    }

    const generation = generationRef.current
    prefetchingRef.current = true
    try {
      const data = await fetchChartData({
        symbolId,
        timeframe,
        start: priorStart,
        end: priorEnd,
        limit: CHUNK_SIZE_BARS,
        indicators: indicatorSpecsRef.current,
      })

      if (generation !== generationRef.current) {
        return
      }

      managerRef.current.addChunk(data.start, {
        candles: data.candles,
        indicators: data.indicators,
      })
      syncAssembled()
    } catch (cause) {
      if (generation === generationRef.current) {
        setError(cause instanceof Error ? cause : new Error(String(cause)))
      }
    } finally {
      if (generation === generationRef.current) {
        prefetchingRef.current = false
      }
    }
  }, [symbolId, syncAssembled, timeframe])

  const onVisibleRangeChange = useCallback(
    (range: LogicalRange | null) => {
      if (!range || status !== 'ready') {
        return
      }

      const from = range.from
      const scrolledLeft =
        lastVisibleFromRef.current != null && from < lastVisibleFromRef.current - 0.5
      lastVisibleFromRef.current = from

      const thresholdIndex = CHUNK_SIZE_BARS * PREFETCH_THRESHOLD
      if (scrolledLeft && from <= thresholdIndex) {
        void prefetchPriorChunk()
      }

      const assembled = candlesRef.current
      const leftIndex = Math.max(0, Math.floor(range.from))
      const leftBar = assembled[leftIndex]
      if (!leftBar) {
        return
      }

      const evictBefore = shiftUnixByBars(
        leftBar.time,
        timeframe,
        LOOKBACK_CHUNKS * CHUNK_SIZE_BARS,
      )
      if (managerRef.current.evictBefore(evictBefore)) {
        syncAssembled()
      }
    },
    [prefetchPriorChunk, status, syncAssembled, timeframe],
  )

  return {
    candles,
    indicators,
    status,
    error,
    onVisibleRangeChange,
  }
}
