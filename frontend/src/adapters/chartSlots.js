import { barChart, gaugeChart, lineChart } from '../utils/chartPresets'

/**
 * Build a single ECharts option from a backend chart slot, or null if fallback.
 * @param {import('../api/dashboard.js').DashboardChartSlot|null} slot
 * @param {string} accent
 * @param {object} def - i18n chart definition (fallback xData)
 * @param {string[]} months - fallback month labels
 */
export function chartOptionFromSlot(slot, accent, def, months) {
  if (!slot || slot.source !== 'live') return null

  if (slot.chart_type === 'gauge' && slot.gauge_value != null) {
    return gaugeChart({ accent, value: slot.gauge_value })
  }

  if (slot.chart_type === 'line' && slot.series?.length) {
    return lineChart({
      accent,
      data: slot.series,
      xData: slot.x_data?.length ? slot.x_data : months
    })
  }

  if (slot.chart_type === 'bar' && slot.series?.length) {
    return barChart({
      accent,
      data: slot.series,
      xData: slot.x_data?.length ? slot.x_data : def?.xData ?? months
    })
  }

  return null
}

/**
 * @param {import('../api/dashboard.js').DashboardChartSlot[]|null|undefined} slots
 * @param {number} index
 */
export function findLiveChartSlot(slots, index) {
  return slots?.find((s) => s.index === index) ?? null
}
