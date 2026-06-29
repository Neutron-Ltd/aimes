<template>
  <div class="assistant-page" :style="{ '--assistant-accent': pageConfig.accent }">
    <AssistantPageHeader
      :title="pageConfig.title"
      :subtitle="pageConfig.subtitle"
      :status-label="t('common.statusAnalyzing')"
    />

    <div class="assistant-workspace-wrap">
      <el-row :gutter="18" class="assistant-workspace">
        <el-col :xs="24" :sm="24" :md="24" :lg="16" :xl="17" class="report-col">
          <main class="report-panel">
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
import AssistantPageHeader from '../../../components/AssistantPageHeader.vue'
import AssistantChartMosaic from '../../../components/AssistantChartMosaic.vue'
import AssistantChatConsole from '../../../components/AssistantChatConsole.vue'
import { useAssistantPage } from '../../../composables/useAssistantPage'
import { buildProductionCharts } from './charts'

const assistantKey = 'production'

const {
  pageConfig,
  charts,
  insightTitle,
  insightText,
  getChartGridStyle,
  setChartRef,
  t
} = useAssistantPage(assistantKey, buildProductionCharts)
</script>
