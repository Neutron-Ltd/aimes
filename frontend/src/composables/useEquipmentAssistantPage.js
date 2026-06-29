import { useIntegratedAssistantPage } from './useIntegratedAssistantPage'
import { buildEquipmentCharts } from '../views/assistants/equipment/charts'

export function useEquipmentAssistantPage() {
  return useIntegratedAssistantPage({
    assistantKey: 'equipment',
    buildChartsFn: buildEquipmentCharts,
    dashboardModule: 'equipment'
  })
}
