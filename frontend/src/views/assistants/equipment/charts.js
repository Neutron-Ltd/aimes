/**
 * AI设备助手 — 独立图表配置
 */
import { barChart, gaugeChart, lineChart } from '../../../utils/chartPresets'
import { buildMosaicCharts } from '../../../utils/chartMosaicLayout'
import { chartOptionFromSlot, findLiveChartSlot } from '../../../adapters/chartSlots'

export function buildEquipmentCharts(accent, chartDefs, months, liveSlots = null) {
  return buildMosaicCharts(chartDefs, (index, def) => {
    const live = findLiveChartSlot(liveSlots, index)
    const liveOption = chartOptionFromSlot(live, accent, def, months)
    if (liveOption) return liveOption

    switch (index) {
      case 0:
        return lineChart({ accent, data: [76, 80, 83, 86, 89, 92], xData: months })
      case 1:
        return barChart({ accent, xData: def.xData, data: [8, 16, 28, 12, 5] })
      case 2:
        return gaugeChart({ accent, value: 84 })
      case 3:
        return barChart({ accent, xData: def.xData, data: [2.4, 1.8, 3.2, 1.1, 0.8] })
      case 4:
        return lineChart({ accent, data: [120, 132, 128, 145, 152, 160], xData: months })
      default:
        return gaugeChart({ accent, value: 91 })
    }
  })
}
