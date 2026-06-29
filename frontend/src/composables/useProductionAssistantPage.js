import { useIntegratedAssistantPage } from './useIntegratedAssistantPage'
import { buildProductionCharts } from '../views/assistants/production/charts'

export function useProductionAssistantPage() {
  return useIntegratedAssistantPage({
    assistantKey: 'production',
    buildChartsFn: buildProductionCharts,
    dashboardModule: 'production'
  })
}
