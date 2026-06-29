import { apiFetch, DEFAULT_LINE_ID } from './client'
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
 * @property {string} line_id
 * @property {DashboardKpiSlot[]} kpis
 * @property {DashboardChartSlot[]} charts
 * @property {string|null} insight
 * @property {boolean} partial
 * @property {string} generated_at
 */

/**
 * @param {string} module
 * @param {{ lineId?: string, locale?: string, lookbackDays?: number }} [options]
 * @returns {Promise<AssistantDashboardResponse>}
 */
export async function getAssistantDashboard(
  module,
  { lineId = DEFAULT_LINE_ID, locale = 'zh', lookbackDays = 7 } = {}
) {
  const params = new URLSearchParams({
    line_id: lineId,
    locale: toApiLocale(locale),
    lookback_days: String(lookbackDays)
  })
  return apiFetch(`/api/v1/assistants/${module}/dashboard?${params}`)
}
