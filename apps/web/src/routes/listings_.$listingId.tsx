import { createFileRoute } from '@tanstack/react-router'

import { fetchListing } from '../api/drivewise'
import { ListingDetailPage } from '../views/ListingDetail'
import { DataRouteError, DataRoutePending } from './-dataStates'
import { loadDetail } from './-detailLoader'

export const Route = createFileRoute('/listings_/$listingId')({
  loader: ({ params }) => loadDetail(() => fetchListing(params.listingId)),
  pendingComponent: DataRoutePending,
  errorComponent: DataRouteError,
  component: ListingDetailRoute,
})

function ListingDetailRoute() {
  return <ListingDetailPage listing={Route.useLoaderData()} />
}
