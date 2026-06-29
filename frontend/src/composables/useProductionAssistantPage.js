import { onMounted, ref, watch } from 'vue'
import { getAssistantDashboard } from '../api/dashboard'
import { extractDashboardLiveData } from '../adapters/production/dashboard'
import { useAssistantPage } from './useAssistantPage'
import { useLocale } from './useLocale'
import { buildProductionCharts } from '../views/assistants/production/charts'

/**
 * Production assistant page with live dashboard data from the backend.
 * Falls back to mock KPIs/charts when the API is unavailable.
 */
export function useProductionAssistantPage() {
  const liveKpis = ref(null)
  const liveChartSlots = ref(null)
  const insightOverride = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const { locale } = useLocale()

  const page = useAssistantPage('production', buildProductionCharts, {
    liveKpis,
    liveChartSlots,
    insightOverride
  })

  async function loadDashboard() {
    loading.value = true
    error.value = null
    try {
      const response = await getAssistantDashboard('production', {
        locale: locale.value
      })
      const live = extractDashboardLiveData(response)
      liveKpis.value = live.kpis
      liveChartSlots.value = live.charts
      insightOverride.value = live.insight
    } catch (err) {
      error.value = err?.message ?? 'Dashboard load failed'
      console.warn('[production dashboard]', err)
    } finally {
      loading.value = false
    }
  }

  onMounted(loadDashboard)
  watch(locale, loadDashboard)

  return {
    ...page,
    loading,
    error,
    reloadDashboard: loadDashboard
  }
}
