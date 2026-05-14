import { createFileRoute } from '@tanstack/react-router'

import { ListingListPage } from '../views/ListingList'

export const Route = createFileRoute('/listings')({
  component: ListingListPage,
})
