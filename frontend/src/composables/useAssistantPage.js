import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { useLocale } from './useLocale'
import { defaultMosaicLayout } from '../utils/chartMosaicLayout'
import '../assets/styles/assistant-dashboard.css'

export function useAssistantPage(assistantKey, buildChartsFn, options = {}) {
  const { liveKpis, liveChartSlots, insightOverride, dashboardLoading } = options
  const { locale, t, getAssistantPageConfig } = useLocale()

  const pageConfig = computed(() => {
    const base = getAssistantPageConfig(assistantKey)
    if (!liveKpis?.value?.length) return base

    const kpis = base.kpis.map((kpi, index) => {
      const live = liveKpis.value.find((s) => s.index === index)
      if (live?.source === 'live') {
        return {
          ...kpi,
          value: live.value,
          trend: live.trend ?? kpi.trend
        }
      }
      return kpi
    })
    return { ...base, kpis }
  })

  const charts = computed(() => {
    if (dashboardLoading?.value) {
      const defs = pageConfig.value.chartDefs || []
      return defaultMosaicLayout.map((layout, index) => ({
        title: defs[index]?.title ?? `Chart ${index + 1}`,
        ...layout,
        option: null
      }))
    }
    return buildChartsFn(
      pageConfig.value.accent,
      pageConfig.value.chartDefs,
      t('common.months'),
      liveChartSlots?.value ?? null
    )
  })

  const chartRefs = ref([])
  const chartInstances = ref([])
  const resizeObservers = []

  const insightTitle = computed(() =>
    t('common.insightTitle', { title: pageConfig.value.title })
  )
  const insightText = computed(() => {
    if (insightOverride?.value) return insightOverride.value
    return t('common.insightText', { subtitle: pageConfig.value.subtitle })
  })

  const getChartGridStyle = (chart) => ({
    gridColumn: `span ${chart.colSpan ?? 4}`,
    gridRow: `span ${chart.rowSpan ?? 1}`
  })

  const disposeChartAt = (index) => {
    resizeObservers[index]?.disconnect()
    delete resizeObservers[index]

    const instance = chartInstances.value[index]
    if (instance) {
      instance.dispose()
      delete chartInstances.value[index]
    }
  }

  const mountChartAt = (el, index) => {
    if (dashboardLoading?.value) return
    const chart = charts.value[index]
    if (!el || !chart?.option) return

    disposeChartAt(index)

    const existing = echarts.getInstanceByDom(el)
    if (existing) existing.dispose()

    const instance = echarts.init(el)
    instance.setOption(chart.option)
    chartInstances.value[index] = instance

    resizeObservers[index] = new ResizeObserver(() => {
      instance.resize()
    })
    resizeObservers[index].observe(el)
    requestAnimationFrame(() => instance.resize())
  }

  const setChartRef = (el, index) => {
    if (dashboardLoading?.value) {
      if (!el) disposeChartAt(index)
      return
    }
    if (el) {
      chartRefs.value[index] = el
      mountChartAt(el, index)
      return
    }

    disposeChartAt(index)
    delete chartRefs.value[index]
  }

  const renderCharts = async () => {
    await nextTick()
    chartRefs.value.forEach((el, index) => {
      if (el) mountChartAt(el, index)
    })
    requestAnimationFrame(resizeCharts)
  }

  const resizeCharts = () => {
    chartInstances.value.forEach((chart) => chart?.resize())
  }

  const disposeAllCharts = () => {
    resizeObservers.forEach((observer) => observer?.disconnect())
    resizeObservers.length = 0
    chartInstances.value.forEach((chart) => chart?.dispose())
    chartInstances.value = []
    chartRefs.value = []
  }

  watch(locale, () => {
    if (!dashboardLoading?.value) renderCharts()
  })
  watch(charts, () => {
    if (!dashboardLoading?.value) renderCharts()
  }, { deep: true, flush: 'post' })
  watch(dashboardLoading, async (isLoading) => {
    if (isLoading) {
      disposeAllCharts()
      return
    }
    await renderCharts()
  })

  onMounted(() => {
    if (!dashboardLoading?.value) {
      renderCharts()
    }
    window.addEventListener('resize', resizeCharts)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', resizeCharts)
    disposeAllCharts()
  })

  return {
    pageConfig,
    charts,
    insightTitle,
    insightText,
    getChartGridStyle,
    setChartRef,
    t
  }
}
