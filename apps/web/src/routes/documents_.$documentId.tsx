import { createFileRoute } from '@tanstack/react-router'

import { DocumentDetailPage } from '../views/DocumentDetail'

export const Route = createFileRoute('/documents_/$documentId')({
  component: DocumentDetailRoute,
})

function DocumentDetailRoute() {
  const { documentId } = Route.useParams()
  return <DocumentDetailPage documentId={documentId} />
}
