<template>
  <div class="chart-mosaic" :class="layoutClass">
    <div
      v-for="(chart, index) in charts"
      :key="chart.title + index"
      class="chart-mosaic-item"
      :class="chart.size ? `chart-mosaic-item--${chart.size}` : ''"
      :style="getChartGridStyle(chart)"
    >
      <el-card class="chart-card" shadow="never">
        <div class="chart-title">
          <span>{{ chart.title }}</span>
          <small>{{ aiAnalysisLabel }}</small>
        </div>
        <div :ref="(el) => setChartRef(el, index)" class="chart-box"></div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
defineProps({
  charts: {
    type: Array,
    required: true
  },
  layoutClass: {
    type: String,
    default: ''
  },
  aiAnalysisLabel: {
    type: String,
    required: true
  },
  getChartGridStyle: {
    type: Function,
    required: true
  },
  setChartRef: {
    type: Function,
    required: true
  }
})
</script>
