import { createFileRoute } from '@tanstack/react-router'

import { VehicleListPage } from '../views/VehicleList'

export const Route = createFileRoute('/vehicles')({
  component: VehicleListPage,
})
