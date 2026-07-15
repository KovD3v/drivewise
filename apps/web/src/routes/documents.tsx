import { createFileRoute } from '@tanstack/react-router'

import { fetchDocuments } from '../api/drivewise'
import { DocumentListPage } from '../views/DocumentList'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/documents')({
  loader: () => fetchDocuments(),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
  component: DocumentsRoute,
})

function DocumentsRoute() {
  return <DocumentListPage initialDocuments={Route.useLoaderData()} />
}
