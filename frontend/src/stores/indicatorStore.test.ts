import { beforeEach, describe, expect, it } from 'vitest'
import { useChartLayoutStore } from '@/stores/chartLayoutStore'
import { useIndicatorStore } from '@/stores/indicatorStore'
import type { IndicatorCatalogEntry } from '@/types/indicator'

const EMA_ENTRY: IndicatorCatalogEntry = {
  key: 'EMA',
  inputs: ['period'],
  sharedParams: [],
  defaultParams: { period: 20 },
  pane: 'overlay',
}

const RSI_ENTRY: IndicatorCatalogEntry = {
  key: 'RSI',
  inputs: ['period'],
  sharedParams: [],
  defaultParams: { period: 14 },
  pane: 'subchart',
}

const BB_ENTRY: IndicatorCatalogEntry = {
  key: 'BB_UPPER',
  inputs: ['period', 'std'],
  sharedParams: ['period', 'std'],
  defaultParams: { period: 20, std: 2 },
  pane: 'overlay',
}

function resetStores() {
  useIndicatorStore.getState().clear()
  useChartLayoutStore.setState({ subPaneHeights: {} })
}

describe('indicatorStore', () => {
  beforeEach(() => {
    resetStores()
  })

  it('adds indicators with custom params, color, and line width', () => {
    const result = useIndicatorStore.getState().addFromCatalog(EMA_ENTRY, {
      params: { period: 25 },
      color: '#ff0000',
      lineWidth: 3,
    })
    expect(result.ok).toBe(true)

    const active = useIndicatorStore.getState().active
    expect(active).toHaveLength(1)
    expect(active[0]?.params).toEqual({ period: 25 })
    expect(active[0]?.seriesId).toBe('EMA_25')
    expect(active[0]?.color).toBe('#ff0000')
    expect(active[0]?.lineWidth).toBe(3)
  })

  it('adds indicators with catalog defaults when no patch is provided', () => {
    const result = useIndicatorStore.getState().addFromCatalog(EMA_ENTRY)
    expect(result.ok).toBe(true)

    const active = useIndicatorStore.getState().active
    expect(active).toHaveLength(1)
    expect(active[0]?.params).toEqual({ period: 20 })
    expect(active[0]?.seriesId).toBe('EMA_20')
    expect(active[0]?.color).toBe('var(--color-accent)')
    expect(active[0]?.lineWidth).toBe(2)
  })

  it('allows multiple instances of the same indicator with different params', () => {
    expect(useIndicatorStore.getState().addFromCatalog(EMA_ENTRY, { params: { period: 20 } }).ok).toBe(
      true,
    )
    expect(useIndicatorStore.getState().addFromCatalog(EMA_ENTRY, { params: { period: 50 } }).ok).toBe(
      true,
    )

    const active = useIndicatorStore.getState().active
    expect(active).toHaveLength(2)
    expect(active.map((item) => item.seriesId).sort()).toEqual(['EMA_20', 'EMA_50'])
    expect(active[0]?.groupInstanceId).not.toBe(active[1]?.groupInstanceId)
  })

  it('allows multiple instances with the same params', () => {
    expect(useIndicatorStore.getState().addFromCatalog(EMA_ENTRY).ok).toBe(true)
    expect(useIndicatorStore.getState().addFromCatalog(EMA_ENTRY).ok).toBe(true)

    const active = useIndicatorStore.getState().active
    expect(active).toHaveLength(2)
    expect(active[0]?.seriesId).toBe('EMA_20')
    expect(active[1]?.seriesId).toBe('EMA_20')
    expect(active[0]?.groupInstanceId).not.toBe(active[1]?.groupInstanceId)
  })

  it('opens settings for an existing indicator instance', () => {
    useIndicatorStore.getState().addFromCatalog(RSI_ENTRY)
    const instanceId = useIndicatorStore.getState().active[0]!.instanceId
    useIndicatorStore.getState().openSettings(instanceId)
    expect(useIndicatorStore.getState().settingsInstanceId).toBe(instanceId)
  })

  it('assigns distinct default colors for multi-line bundle indicators', () => {
    useIndicatorStore.getState().addFromCatalog(BB_ENTRY)
    const active = useIndicatorStore.getState().active
    expect(active).toHaveLength(3)
    const colors = active.map((item) => item.color)
    expect(new Set(colors).size).toBe(3)
    expect(active.map((item) => item.key).sort()).toEqual(['BB_LOWER', 'BB_MIDDLE', 'BB_UPPER'])
  })

  it('updates per-series style within a bundle', () => {
    useIndicatorStore.getState().addFromCatalog(BB_ENTRY)
    const instanceId = useIndicatorStore.getState().active[0]!.instanceId

    const result = useIndicatorStore.getState().updateIndicatorSettings(instanceId, {
      seriesStyles: {
        BB_UPPER: { color: '#111111', lineWidth: 3 },
        BB_MIDDLE: { color: '#222222', lineWidth: 2 },
        BB_LOWER: { color: '#333333', lineWidth: 1 },
      },
    })
    expect(result.ok).toBe(true)

    const byKey = Object.fromEntries(
      useIndicatorStore.getState().active.map((item) => [item.key, item]),
    )
    expect(byKey.BB_UPPER?.color).toBe('#111111')
    expect(byKey.BB_UPPER?.lineWidth).toBe(3)
    expect(byKey.BB_MIDDLE?.color).toBe('#222222')
    expect(byKey.BB_LOWER?.color).toBe('#333333')
  })

  it('updates per-series visibility within a bundle', () => {
    useIndicatorStore.getState().addFromCatalog(BB_ENTRY)
    const instanceId = useIndicatorStore.getState().active[0]!.instanceId

    const result = useIndicatorStore.getState().updateIndicatorSettings(instanceId, {
      seriesStyles: {
        BB_UPPER: { visible: false },
        BB_MIDDLE: { visible: true },
        BB_LOWER: { visible: true },
      },
    })
    expect(result.ok).toBe(true)

    const byKey = Object.fromEntries(
      useIndicatorStore.getState().active.map((item) => [item.key, item]),
    )
    expect(byKey.BB_UPPER?.visible).toBe(false)
    expect(byKey.BB_MIDDLE?.visible).toBe(true)
    expect(byKey.BB_LOWER?.visible).toBe(true)
  })

  it('updates appearance without changing params', () => {
    useIndicatorStore.getState().addFromCatalog(EMA_ENTRY)
    const instanceId = useIndicatorStore.getState().active[0]!.instanceId

    const result = useIndicatorStore.getState().updateIndicatorSettings(instanceId, {
      seriesStyles: {
        EMA: { color: '#00ff00', lineWidth: 4 },
      },
    })
    expect(result.ok).toBe(true)

    const updated = useIndicatorStore.getState().active[0]
    expect(updated?.color).toBe('#00ff00')
    expect(updated?.lineWidth).toBe(4)
    expect(updated?.params).toEqual({ period: 20 })
  })

  it('keeps sub-pane layout when subchart params change', () => {
    useIndicatorStore.getState().addFromCatalog(RSI_ENTRY, { params: { period: 14 } })
    const instanceId = useIndicatorStore.getState().active[0]!.instanceId
    const groupInstanceId = useIndicatorStore.getState().active[0]!.groupInstanceId
    useChartLayoutStore.getState().setSubPaneHeight(groupInstanceId, 180)

    const result = useIndicatorStore.getState().updateIndicatorSettings(instanceId, {
      params: { period: 21 },
    })
    expect(result.ok).toBe(true)

    expect(useChartLayoutStore.getState().subPaneHeights[groupInstanceId]).toBe(180)
    expect(useIndicatorStore.getState().active[0]?.seriesId).toBe('RSI_21')
  })

  it('updates only the targeted instance when params change', () => {
    useIndicatorStore.getState().addFromCatalog(EMA_ENTRY, { params: { period: 20 } })
    useIndicatorStore.getState().addFromCatalog(EMA_ENTRY, { params: { period: 50 } })
    const toUpdate = useIndicatorStore
      .getState()
      .active.find((item) => item.params.period === 50)!.instanceId

    const result = useIndicatorStore.getState().updateIndicatorSettings(toUpdate, {
      params: { period: 100 },
    })
    expect(result.ok).toBe(true)

    const active = useIndicatorStore.getState().active
    expect(active.find((item) => item.params.period === 20)?.seriesId).toBe('EMA_20')
    expect(active.find((item) => item.params.period === 100)?.seriesId).toBe('EMA_100')
  })
})
