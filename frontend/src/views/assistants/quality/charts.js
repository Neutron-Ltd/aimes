/**
 * AI质量助手 — 独立图表配置
 */
import { barChart, gaugeChart, lineChart } from '../../../utils/chartPresets'
import { buildMosaicCharts } from '../../../utils/chartMosaicLayout'
import { chartOptionFromSlot, findLiveChartSlot } from '../../../adapters/chartSlots'

export function buildQualityCharts(accent, chartDefs, months, liveSlots = null) {
  return buildMosaicCharts(chartDefs, (index, def) => {
    const live = findLiveChartSlot(liveSlots, index)
    const liveOption = chartOptionFromSlot(live, accent, def, months)
    if (liveOption) return liveOption

    switch (index) {
      case 0:
        return lineChart({ accent, data: [3.2, 2.8, 2.5, 1.9, 1.6, 1.3], xData: months })
      case 1:
        return barChart({ accent, xData: def.xData, data: [18, 12, 9, 6, 4] })
      case 2:
        return gaugeChart({ accent, value: 92 })
      case 3:
        return lineChart({ accent, data: [2.4, 2.1, 1.8, 1.5, 1.2, 0.9], xData: months })
      case 4:
        return barChart({ accent, xData: def.xData, data: [98, 96, 94, 97, 95] })
      default:
        return gaugeChart({ accent, value: 97 })
    }
  })
}
