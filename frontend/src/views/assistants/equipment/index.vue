<template>
  <AssistantDashboardLayout
    :assistant-key="assistantKey"
    :page-config="pageConfig"
    :charts="charts"
    :insight-title="insightTitle"
    :insight-text="insightText"
    :get-chart-grid-style="getChartGridStyle"
    :set-chart-ref="setChartRef"
    :loading="loading"
    :error="error"
    :reload-dashboard="reloadDashboard"
    :t="t"
  />
</template>

<script setup>
import AssistantDashboardLayout from '../../../components/AssistantDashboardLayout.vue'
import { useEquipmentAssistantPage } from '../../../composables/useEquipmentAssistantPage'

const assistantKey = 'equipment'

const {
  pageConfig,
  charts,
  insightTitle,
  insightText,
  getChartGridStyle,
  setChartRef,
  loading,
  error,
  reloadDashboard,
  t
} = useEquipmentAssistantPage()
</script>
