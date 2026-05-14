import { createFileRoute } from '@tanstack/react-router'

import { AdvisorPage } from '../views/Advisor'

export const Route = createFileRoute('/advisor')({
  component: AdvisorPage,
})
