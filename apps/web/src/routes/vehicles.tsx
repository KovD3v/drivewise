import { createFileRoute } from '@tanstack/react-router'

import { fetchVehicles } from '../api/drivewise'
import { VehicleListPage } from '../views/VehicleList'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/vehicles')({
  loader: () => fetchVehicles(),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
  component: VehiclesRoute,
})

function VehiclesRoute() {
  return <VehicleListPage initialVehicles={Route.useLoaderData()} />
}
