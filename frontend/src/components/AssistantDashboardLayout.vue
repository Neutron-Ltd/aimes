<template>
  <div class="assistant-page" :style="{ '--assistant-accent': pageConfig.accent }">
    <AssistantPageHeader
      :title="pageConfig.title"
      :subtitle="pageConfig.subtitle"
      :status-label="statusLabel"
    />

    <div class="assistant-workspace-wrap">
      <el-row :gutter="18" class="assistant-workspace">
        <el-col :xs="24" :sm="24" :md="24" :lg="16" :xl="17" class="report-col">
          <main
            class="report-panel"
            :class="{ 'report-panel--loading': loading }"
          >
            <el-alert
              v-if="error && !loading"
              type="warning"
              :title="t('common.dashboardError')"
              :description="error"
              show-icon
              class="dashboard-error-alert"
            >
              <template #default>
                <el-button size="small" type="primary" @click="reloadDashboard">
                  {{ t('common.dashboardRetry') }}
                </el-button>
              </template>
            </el-alert>

            <template v-if="loading">
              <p class="dashboard-loading-label">{{ t('common.dashboardLoading') }}</p>
              <el-row :gutter="8" class="kpi-grid">
                <el-col v-for="n in 3" :key="n" :xs="24" :sm="8">
                  <el-card class="kpi-card kpi-card--skeleton" shadow="never">
                    <el-skeleton animated :rows="2" />
                  </el-card>
                </el-col>
              </el-row>

              <div class="chart-mosaic chart-mosaic--skeleton" :class="pageConfig.layout">
                <div
                  v-for="(chart, index) in charts"
                  :key="'sk-' + index"
                  class="chart-mosaic-item"
                  :style="getChartGridStyle(chart)"
                >
                  <el-card class="chart-card" shadow="never">
                    <el-skeleton animated :rows="0" />
                    <div class="chart-box chart-box--skeleton">
                      <el-skeleton animated :rows="4" />
                    </div>
                  </el-card>
                </div>
              </div>

              <el-card class="insight-card insight-card--skeleton" shadow="never">
                <el-skeleton animated :rows="3" />
              </el-card>
            </template>

            <template v-else>
              <el-row :gutter="8" class="kpi-grid">
                <el-col v-for="item in pageConfig.kpis" :key="item.label" :xs="24" :sm="8">
                  <el-card class="kpi-card" shadow="never">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                    <em>{{ item.trend }}</em>
                  </el-card>
                </el-col>
              </el-row>

              <AssistantChartMosaic
                :charts="charts"
                :layout-class="pageConfig.layout"
                :ai-analysis-label="t('common.aiAnalysis')"
                :get-chart-grid-style="getChartGridStyle"
                :set-chart-ref="setChartRef"
              />

              <el-card class="insight-card" shadow="never">
                <div>
                  <span class="insight-label">{{ t('common.insight') }}</span>
                  <h3>{{ insightTitle }}</h3>
                  <p>{{ insightText }}</p>
                </div>
                <div class="pulse-orb"></div>
              </el-card>
            </template>
          </main>
        </el-col>

        <AssistantChatConsole
          :assistant-key="assistantKey"
          :title="pageConfig.title"
          :greeting="pageConfig.greeting"
          :prompts="pageConfig.prompts"
          :avatar="pageConfig.avatar"
          :accent="pageConfig.accent"
        />
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AssistantPageHeader from './AssistantPageHeader.vue'
import AssistantChartMosaic from './AssistantChartMosaic.vue'
import AssistantChatConsole from './AssistantChatConsole.vue'

const props = defineProps({
  assistantKey: {
    type: String,
    required: true
  },
  pageConfig: {
    type: Object,
    required: true
  },
  charts: {
    type: Array,
    required: true
  },
  insightTitle: {
    type: String,
    required: true
  },
  insightText: {
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
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  reloadDashboard: {
    type: Function,
    required: true
  },
  t: {
    type: Function,
    required: true
  }
})

const statusLabel = computed(() =>
  props.loading ? props.t('common.statusAnalyzing') : props.t('common.statusReady')
)
</script>
