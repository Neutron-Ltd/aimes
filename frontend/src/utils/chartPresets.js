/** 可选图表预设 — 各助手 charts.js 可自由选用或完全自定义 ECharts option */

const compactGrid = { left: 28, right: 8, top: 16, bottom: 20 }

export const axisStyle = {
  axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.25)' } },
  axisTick: { show: false },
  axisLabel: { color: '#94a3b8', fontSize: 9 },
  splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
}

export const monthLabels = ['1月', '2月', '3月', '4月', '5月', '6月']

export function lineChart({ accent, data, xData = monthLabels }) {
  return {
    grid: compactGrid,
    tooltip: {
      trigger: 'axis',
      confine: true,
      appendToBody: false,
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: accent,
      textStyle: { color: '#e0f2fe', fontSize: 10 }
    },
    xAxis: { type: 'category', data: xData, ...axisStyle },
    yAxis: { type: 'value', ...axisStyle },
    series: [{
      type: 'line',
      data,
      smooth: true,
      symbolSize: 4,
      itemStyle: { color: accent },
      areaStyle: { color: `${accent}24` },
      lineStyle: { color: accent, width: 2 }
    }]
  }
}

export function barChart({ accent, data, xData = monthLabels }) {
  return {
    grid: compactGrid,
    tooltip: {
      trigger: 'axis',
      confine: true,
      appendToBody: false,
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: accent,
      textStyle: { color: '#e0f2fe', fontSize: 10 }
    },
    xAxis: { type: 'category', data: xData, ...axisStyle },
    yAxis: { type: 'value', ...axisStyle },
    series: [{
      type: 'bar',
      data,
      barWidth: 10,
      itemStyle: { color: accent, borderRadius: [2, 2, 0, 0] }
    }]
  }
}

export function gaugeChart({ accent, value }) {
  return {
    series: [{
      type: 'gauge',
      radius: '86%',
      progress: { show: true, width: 7, itemStyle: { color: accent } },
      axisLine: { lineStyle: { width: 7, color: [[1, 'rgba(59, 130, 246, 0.18)']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { width: 3, itemStyle: { color: accent } },
      detail: {
        valueAnimation: true,
        color: '#e0f2fe',
        fontSize: 14,
        offsetCenter: [0, '14%'],
        formatter: '{value}%'
      },
      data: [{ value }]
    }]
  }
}
