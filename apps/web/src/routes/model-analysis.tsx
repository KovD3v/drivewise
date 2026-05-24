import { createFileRoute } from '@tanstack/react-router'

import { ModelAnalysisPage } from '../views/ModelAnalysis'

export const Route = createFileRoute('/model-analysis')({
  component: ModelAnalysisPage,
})
