import { createFileRoute } from '@tanstack/react-router'

import { fetchVehicle } from '../api/drivewise'
import { VehicleDetailPage } from '../views/VehicleDetail'
import { DataRouteError, DataRoutePending } from './-dataStates'
import { loadDetail } from './-detailLoader'

export const Route = createFileRoute('/vehicles_/$vehicleId')({
  loader: ({ params }) => loadDetail(() => fetchVehicle(params.vehicleId)),
  pendingComponent: DataRoutePending,
  errorComponent: DataRouteError,
  component: VehicleDetailRoute,
})

function VehicleDetailRoute() {
  return <VehicleDetailPage vehicle={Route.useLoaderData()} />
}
