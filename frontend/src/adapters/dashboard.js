/**
 * @param {import('../api/dashboard.js').AssistantDashboardResponse} response
 */
export function extractDashboardLiveData(response) {
  return {
    kpis: response.kpis ?? [],
    charts: response.charts ?? [],
    insight: response.insight ?? null,
    partial: response.partial ?? false
  }
}

/**
 * Merge backend dashboard KPI slots into i18n-based page config KPIs.
 * @param {import('../api/dashboard.js').DashboardKpiSlot[]|null|undefined} liveKpis
 * @param {Array<{ label: string, value: string, trend: string }>} baseKpis
 */
export function mergeKpiSlots(liveKpis, baseKpis) {
  if (!liveKpis?.length) return baseKpis

  return baseKpis.map((kpi, index) => {
    const live = liveKpis.find((s) => s.index === index)
    if (live?.source === 'live') {
      return {
        ...kpi,
        value: live.value,
        trend: live.trend ?? kpi.trend
      }
    }
    return kpi
  })
}
