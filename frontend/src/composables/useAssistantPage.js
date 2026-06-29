import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { useLocale } from './useLocale'
import '../assets/styles/assistant-dashboard.css'

export function useAssistantPage(assistantKey, buildChartsFn) {
  const { locale, t, getAssistantPageConfig } = useLocale()

  const pageConfig = computed(() => getAssistantPageConfig(assistantKey))
  const charts = computed(() =>
    buildChartsFn(
      pageConfig.value.accent,
      pageConfig.value.chartDefs,
      t('common.months')
    )
  )

  const chartRefs = ref([])
  const chartInstances = ref([])
  const resizeObservers = []

  const insightTitle = computed(() =>
    t('common.insightTitle', { title: pageConfig.value.title })
  )
  const insightText = computed(() =>
    t('common.insightText', { subtitle: pageConfig.value.subtitle })
  )

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

  watch(locale, renderCharts)
  watch(charts, renderCharts, { deep: true, flush: 'post' })

  onMounted(() => {
    renderCharts()
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
