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
          <main class="report-panel">
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

            <el-row :gutter="8" class="kpi-grid">
              <el-col v-for="item in pageConfig.kpis" :key="item.label" :xs="24" :sm="8">
                <el-card class="kpi-card" shadow="never">
                  <span>{{ item.label }}</span>
                  <strong>{{ loading ? t('common.loading') : item.value }}</strong>
                  <em>{{ loading ? t('common.loading') : item.trend }}</em>
                </el-card>
              </el-col>
            </el-row>

            <AssistantChartMosaic
              :charts="charts"
              :layout-class="pageConfig.layout"
              :ai-analysis-label="t('common.aiAnalysis')"
              :loading-label="t('common.loading')"
              :loading="loading"
              :get-chart-grid-style="getChartGridStyle"
              :set-chart-ref="setChartRef"
            />

            <el-card class="insight-card" shadow="never">
              <div>
                <span class="insight-label">{{ t('common.insight') }}</span>
                <h3>{{ insightTitle }}</h3>
                <p>{{ loading ? t('common.loading') : insightText }}</p>
              </div>
              <div class="pulse-orb"></div>
            </el-card>
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
