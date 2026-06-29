import { useIntegratedAssistantPage } from './useIntegratedAssistantPage'
import { buildQualityCharts } from '../views/assistants/quality/charts'

export function useQualityAssistantPage() {
  return useIntegratedAssistantPage({
    assistantKey: 'quality',
    buildChartsFn: buildQualityCharts,
    dashboardModule: 'quality'
  })
}
