import { onMounted, ref, watch } from 'vue'
import { getAssistantDashboard } from '../api/dashboard'
import { extractDashboardLiveData } from '../adapters/dashboard'
import { useAssistantPage } from './useAssistantPage'
import { useLocale } from './useLocale'

/**
 * Generic integrated assistant page — loads dashboard snapshot from backend.
 * @param {{ assistantKey: string, buildChartsFn: Function, dashboardModule?: string }} options
 */
export function useIntegratedAssistantPage({
  assistantKey,
  buildChartsFn,
  dashboardModule = assistantKey
}) {
  const liveKpis = ref(null)
  const liveChartSlots = ref(null)
  const insightOverride = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const { locale } = useLocale()

  const page = useAssistantPage(assistantKey, buildChartsFn, {
    liveKpis,
    liveChartSlots,
    insightOverride
  })

  async function loadDashboard() {
    loading.value = true
    error.value = null
    try {
      const response = await getAssistantDashboard(dashboardModule, {
        locale: locale.value
      })
      const live = extractDashboardLiveData(response)
      liveKpis.value = live.kpis
      liveChartSlots.value = live.charts
      insightOverride.value = live.insight
    } catch (err) {
      error.value = err?.message ?? 'Dashboard load failed'
      console.warn(`[${assistantKey} dashboard]`, err)
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
