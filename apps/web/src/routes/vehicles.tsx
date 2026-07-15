import { createFileRoute } from '@tanstack/react-router'

import { fetchVehicles } from '../api/drivewise'
import { VehicleListPage } from '../views/VehicleList'
import { validateVehicleSearch } from './-collectionSearch'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

export const Route = createFileRoute('/vehicles')({
  validateSearch: validateVehicleSearch,
  loaderDeps: ({ search }) => search,
  loader: ({ deps }) => fetchVehicles(deps),
  pendingComponent: CollectionRoutePending,
  errorComponent: CollectionRouteError,
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
