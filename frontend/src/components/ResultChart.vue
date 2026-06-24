<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { buildChartPayload } from '../utils/chartData'
import type { ChartPayload } from '../utils/chartData'

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, TitleComponent, CanvasRenderer])

const props = defineProps<{
  result: Record<string, unknown> | unknown[] | null
}>()

const { t } = useI18n()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const payload = computed<ChartPayload | null>(() => buildChartPayload(props.result))

const MES_THEME = {
  sky: '#38bdf8',
  skyDim: '#0ea5e9',
  emerald: '#34d399',
  zinc400: '#a1a1aa',
  zinc600: '#52525b',
  zinc700: '#3f3f46',
  zinc800: '#27272a',
  zinc900: '#18181b',
}

function buildOption(data: ChartPayload): echarts.EChartsCoreOption {
  const categories = data.points.map((p) => p.label)
  const values = data.points.map((p) => p.value)
  const isLine = data.chartType === 'line'

  const series = isLine
    ? {
        type: 'line' as const,
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: MES_THEME.sky, width: 2 },
        itemStyle: { color: MES_THEME.sky },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.25)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0)' },
          ]),
        },
      }
    : {
        type: 'bar' as const,
        data: values,
        barMaxWidth: 40,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: MES_THEME.sky },
            { offset: 1, color: MES_THEME.skyDim },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      }

  return {
    backgroundColor: 'transparent',
    title: data.title
      ? {
          text: data.title,
          left: 0,
          top: 0,
          textStyle: { color: MES_THEME.zinc400, fontSize: 11, fontWeight: 500 },
        }
      : undefined,
    grid: { left: 48, right: 16, top: data.title ? 36 : 16, bottom: 48 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: MES_THEME.zinc800,
      borderColor: MES_THEME.zinc700,
      textStyle: { color: '#e4e4e7', fontSize: 12 },
      axisPointer: { type: isLine ? 'line' : 'shadow', lineStyle: { color: MES_THEME.zinc600 } },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params]
        const first = items[0] as { name?: string; value?: number } | undefined
        if (!first) return ''
        return `<strong>${first.name}</strong><br/>${data.yAxisLabel}: <span style="color:${MES_THEME.emerald}">${first.value}</span>`
      },
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: MES_THEME.zinc700 } },
      axisTick: { show: false },
      axisLabel: {
        color: MES_THEME.zinc400,
        fontSize: 10,
        rotate: categories.length > 6 ? 35 : 0,
        interval: 0,
      },
    },
    yAxis: {
      type: 'value',
      name: data.yAxisLabel,
      nameTextStyle: { color: MES_THEME.zinc400, fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: MES_THEME.zinc800, type: 'dashed' } },
      axisLabel: { color: MES_THEME.zinc400, fontSize: 10 },
    },
    series: [series],
  }
}

function renderChart() {
  if (!chartRef.value || !payload.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  }

  chartInstance.setOption(buildOption(payload.value), { notMerge: true })
}

function disposeChart() {
  resizeObserver?.disconnect()
  resizeObserver = null
  chartInstance?.dispose()
  chartInstance = null
}

onMounted(() => {
  renderChart()
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => chartInstance?.resize())
    resizeObserver.observe(chartRef.value)
  }
})

onBeforeUnmount(disposeChart)

watch(payload, () => {
  if (payload.value) {
    renderChart()
  } else {
    disposeChart()
  }
}, { deep: true })
</script>

<template>
  <div
    v-if="payload"
    class="mb-3 overflow-hidden rounded-lg border border-zinc-700/60 bg-zinc-950/60"
  >
    <div class="border-b border-zinc-800/80 px-3 py-2">
      <span class="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
        {{ t('chat.dataVisualization') }}
      </span>
    </div>
    <div ref="chartRef" class="h-52 w-full" />
  </div>
</template>
