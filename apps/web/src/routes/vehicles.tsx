import { createFileRoute } from '@tanstack/react-router'

import { fetchVehicles } from '../api/drivewise'
import { VehicleListPage } from '../views/VehicleList'
import { validateVehicleSearch } from './-collectionSearch'
import { DataRouteError, DataRoutePending } from './-dataStates'

export const Route = createFileRoute('/vehicles')({
  validateSearch: validateVehicleSearch,
  loaderDeps: ({ search }) => search,
  loader: ({ deps }) => fetchVehicles(deps),
  pendingComponent: DataRoutePending,
  errorComponent: DataRouteError,
  component: VehiclesRoute,
})

function VehiclesRoute() {
  const filters = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <VehicleListPage
      filters={filters}
      onFiltersChange={(search) => void navigate({ search })}
      vehicles={Route.useLoaderData()}
    />
  )
}
