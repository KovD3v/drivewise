import { fireEvent, screen } from '@testing-library/react'
import { test, expect, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { VehicleListPage } from './VehicleList'

const vehiclesResponse = [
  {
    id: '00000000-0000-4000-8000-000000000001',
    make: 'Fiat',
    model: 'Panda',
    model_year: 2024,
    body_style: 'city_car',
    fuel_type: 'mild_hybrid_petrol',
    market: 'IT',
    base_price_eur: 15500,
  },
]

test('renders loader data and submits URL filter state', () => {
  const onFiltersChange = vi.fn()
  renderWithRouter(
    <VehicleListPage
      filters={{}}
      onFiltersChange={onFiltersChange}
      vehicles={vehiclesResponse}
    />,
  )

  expect(screen.getByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('2024 · city_car')).toBeVisible()
  expect(screen.getByText('mild_hybrid_petrol')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio veicolo' })).toHaveAttribute(
    'href',
    '/vehicles/00000000-0000-4000-8000-000000000001',
  )

  fireEvent.change(screen.getByLabelText('Make'), {
    target: { value: 'Fiat' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Applica filtri' }))

  expect(onFiltersChange).toHaveBeenCalledWith({
    make: 'Fiat',
    fuel_type: undefined,
    body_style: undefined,
    market: undefined,
    max_price_eur: undefined,
  })
})
