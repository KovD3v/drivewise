import { createFileRoute } from '@tanstack/react-router'

import { fetchDocument } from '../api/drivewise'
import { DocumentDetailPage } from '../views/DocumentDetail'
import { DataRouteError, DataRoutePending } from './-dataStates'
import { loadDetail } from './-detailLoader'

export const Route = createFileRoute('/documents_/$documentId')({
  loader: ({ params }) => loadDetail(() => fetchDocument(params.documentId)),
  pendingComponent: DataRoutePending,
  errorComponent: DataRouteError,
  component: DocumentDetailRoute,
})

function DocumentDetailRoute() {
  return <DocumentDetailPage document={Route.useLoaderData()} />
}
