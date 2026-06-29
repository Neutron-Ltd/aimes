/**
 * AI仓库助手 — 独立图表配置
 */
import { barChart, gaugeChart, lineChart } from '../../../utils/chartPresets'
import { buildMosaicCharts } from '../../../utils/chartMosaicLayout'

export function buildWarehouseCharts(accent, chartDefs, months) {
  return buildMosaicCharts(chartDefs, (index, def) => {
    switch (index) {
      case 0:
        return barChart({ accent, data: [58, 76, 64, 88, 72, 95], xData: months })
      case 1:
        return lineChart({ accent, data: [52, 49, 46, 44, 40, 37], xData: months })
      case 2:
        return gaugeChart({ accent, value: 78 })
      case 3:
        return barChart({ accent, xData: def.xData, data: [120, 86, 54, 38, 22] })
      case 4:
        return lineChart({ accent, data: [68, 72, 75, 79, 82, 86], xData: months })
      default:
        return gaugeChart({ accent, value: 94 })
    }
  })
}
