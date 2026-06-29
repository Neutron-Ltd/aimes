/**
 * AI生产助手 — 独立图表配置
 */
import { barChart, gaugeChart, lineChart } from '../../../utils/chartPresets'
import { buildMosaicCharts } from '../../../utils/chartMosaicLayout'
import { chartOptionFromSlot, findLiveChartSlot } from '../../../adapters/chartSlots'

export function buildProductionCharts(accent, chartDefs, months, liveSlots = null) {
  return buildMosaicCharts(chartDefs, (index, def) => {
    const live = findLiveChartSlot(liveSlots, index)
    const liveOption = chartOptionFromSlot(live, accent, def, months)
    if (liveOption) return liveOption

    switch (index) {
      case 0:
        return lineChart({ accent, data: [82, 88, 91, 90, 96, 98], xData: months })
      case 1:
        return barChart({ accent, xData: def.xData, data: [42, 28, 18, 9, 5] })
      case 2:
        return gaugeChart({ accent, value: 86 })
      case 3:
        return barChart({ accent, xData: def.xData, data: [88, 92, 76, 84, 79] })
      case 4:
        return lineChart({ accent, data: [74, 78, 81, 83, 85, 87], xData: months })
      default:
        return barChart({ accent, xData: def.xData, data: [32, 24, 18, 12, 8] })
    }
  })
}
