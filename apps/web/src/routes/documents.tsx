import { createFileRoute } from '@tanstack/react-router'

import { DocumentListPage } from '../views/DocumentList'

export const Route = createFileRoute('/documents')({
  component: DocumentListPage,
})
