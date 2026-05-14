import { createFileRoute } from '@tanstack/react-router'

import { ListingDetailPage } from '../views/ListingDetail'

export const Route = createFileRoute('/listings_/$listingId')({
  component: ListingDetailRoute,
})

function ListingDetailRoute() {
  const { listingId } = Route.useParams()
  return <ListingDetailPage listingId={listingId} />
}
