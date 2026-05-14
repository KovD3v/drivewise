import { createFileRoute } from '@tanstack/react-router'

import { DocumentSearchPage } from '../views/DocumentSearch'

export const Route = createFileRoute('/search')({
  component: DocumentSearchPage,
})
