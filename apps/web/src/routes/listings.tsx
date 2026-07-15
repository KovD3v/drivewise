import { createFileRoute } from '@tanstack/react-router'

import { fetchListings } from '../api/drivewise'
import { ListingListPage } from '../views/ListingList'
import { validateListingSearch } from './-collectionSearch'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/listings')({
  validateSearch: validateListingSearch,
  loaderDeps: ({ search }) => search,
  loader: ({ deps }) => fetchListings(deps),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
  component: ListingsRoute,
})

function ListingsRoute() {
  const filters = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <ListingListPage
      filters={filters}
      listings={Route.useLoaderData()}
      onFiltersChange={(search) => void navigate({ search })}
    />
  )
}
