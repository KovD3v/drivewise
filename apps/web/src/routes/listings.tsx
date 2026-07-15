import { createFileRoute } from '@tanstack/react-router'

import { fetchListings } from '../api/drivewise'
import { ListingListPage } from '../views/ListingList'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/listings')({
  loader: () => fetchListings(),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
  component: ListingsRoute,
})

function ListingsRoute() {
  return <ListingListPage initialListings={Route.useLoaderData()} />
}
