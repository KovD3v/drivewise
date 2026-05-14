import { createFileRoute } from '@tanstack/react-router'

import { VehicleDetailPage } from '../views/VehicleDetail'

export const Route = createFileRoute('/vehicles/$vehicleId')({
  component: VehicleDetailRoute,
})

function VehicleDetailRoute() {
  const { vehicleId } = Route.useParams()
  return <VehicleDetailPage vehicleId={vehicleId} />
}
