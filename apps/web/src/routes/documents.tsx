import { createFileRoute } from '@tanstack/react-router'

import { fetchDocuments } from '../api/drivewise'
import { DocumentListPage } from '../views/DocumentList'
import { validateDocumentSearch } from './-collectionSearch'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/documents')({
  validateSearch: validateDocumentSearch,
  loaderDeps: ({ search }) => search,
  loader: ({ deps }) => fetchDocuments(deps),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
  component: DocumentsRoute,
})

function DocumentsRoute() {
  const filters = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <DocumentListPage
      documents={Route.useLoaderData()}
      filters={filters}
      onFiltersChange={(search) => void navigate({ search })}
    />
  )
}
