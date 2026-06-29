/**
 * AI采购助手 — 独立图表配置
 */
import { barChart, gaugeChart, lineChart } from '../../../utils/chartPresets'
import { buildMosaicCharts } from '../../../utils/chartMosaicLayout'

export function buildProcurementCharts(accent, chartDefs, months) {
  return buildMosaicCharts(chartDefs, (index, def) => {
    switch (index) {
      case 0:
        return lineChart({ accent, data: [68, 74, 70, 82, 77, 88], xData: months })
      case 1:
        return barChart({ accent, xData: def.xData, data: [96, 88, 84, 79, 72] })
      case 2:
        return gaugeChart({ accent, value: 89 })
      case 3:
        return barChart({ accent, xData: def.xData, data: [12, 15, 18, 21, 24] })
      case 4:
        return lineChart({ accent, data: [5.2, 5.8, 6.1, 5.6, 6.4, 6.8], xData: months })
      default:
        return gaugeChart({ accent, value: 93 })
    }
  })
}
