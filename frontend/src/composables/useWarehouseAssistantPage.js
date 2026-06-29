import { useIntegratedAssistantPage } from './useIntegratedAssistantPage'
import { buildWarehouseCharts } from '../views/assistants/warehouse/charts'

export function useWarehouseAssistantPage() {
  return useIntegratedAssistantPage({
    assistantKey: 'warehouse',
    buildChartsFn: buildWarehouseCharts,
    dashboardModule: 'warehouse'
  })
}
