import { apiFetch, DEFAULT_LINE_ID, DEFAULT_WH_CODE } from './client'
import { toApiLocale } from './locale'

/**
 * @typedef {Object} DashboardKpiSlot
 * @property {number} index
 * @property {string} value
 * @property {string|null} [trend]
 * @property {'live'|'fallback'} source
 */

/**
 * @typedef {Object} DashboardChartSlot
 * @property {number} index
 * @property {'line'|'bar'|'gauge'} chart_type
 * @property {string[]} x_data
 * @property {number[]} series
 * @property {number|null} [gauge_value]
 * @property {'live'|'fallback'} source
 */

/**
 * @typedef {Object} AssistantDashboardResponse
 * @property {string} module
 * @property {string|null} [line_id]
 * @property {string|null} [wh_code]
 * @property {DashboardKpiSlot[]} kpis
 * @property {DashboardChartSlot[]} charts
 * @property {string|null} insight
 * @property {boolean} partial
 * @property {string} generated_at
 */

/**
 * @param {string} module
 * @param {{ lineId?: string, whCode?: string, locale?: string, lookbackDays?: number }} [options]
 * @returns {Promise<AssistantDashboardResponse>}
 */
export async function getAssistantDashboard(
  module,
  {
    lineId = DEFAULT_LINE_ID,
    whCode = DEFAULT_WH_CODE,
    locale = 'zh',
    lookbackDays = 7
  } = {}
) {
  const params = new URLSearchParams({
    locale: toApiLocale(locale),
    lookback_days: String(lookbackDays)
  })

  if (module === 'production' || module === 'quality' || module === 'equipment') {
    params.set('line_id', lineId)
  } else if (module === 'warehouse' && whCode) {
    params.set('wh_code', whCode)
  }

  return apiFetch(`/api/v1/assistants/${module}/dashboard?${params}`)
}
