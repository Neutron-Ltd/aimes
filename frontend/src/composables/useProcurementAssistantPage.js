import { useIntegratedAssistantPage } from './useIntegratedAssistantPage'
import { buildProcurementCharts } from '../views/assistants/procurement/charts'

export function useProcurementAssistantPage() {
  return useIntegratedAssistantPage({
    assistantKey: 'procurement',
    buildChartsFn: buildProcurementCharts,
    dashboardModule: 'procurement'
  })
}
