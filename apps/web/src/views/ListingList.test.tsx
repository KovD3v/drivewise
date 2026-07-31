import { fireEvent, screen } from '@testing-library/react'
import { test, expect, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { ListingListPage } from './ListingList'

const listingsResponse = [
  {
    id: '30000000-0000-4000-8000-000000000001',
    vehicle_id: '00000000-0000-4000-8000-000000000001',
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-fiat-panda-2024-it',
    title: 'Fiat Panda 1.0 FireFly Hybrid',
    price_eur: 14200,
    mileage: 6400,
    condition: 'used',
    location_region: 'Piemonte',
    listed_at: '2026-01-15',
    vehicle: {
      id: '00000000-0000-4000-8000-000000000001',
      canonical_key: 'fiat-panda-2024-it',
      model_family_key: 'fiat-panda',
      make: 'Fiat',
      model: 'Panda',
      model_year: 2024,
      body_style: 'city_car',
      fuel_type: 'mild_hybrid_petrol',
      market: 'IT',
      base_price_eur: 15500,
    },
  },
]

test('renders loader data and submits URL filter state', () => {
  const onFiltersChange = vi.fn()
  renderWithRouter(
    <ListingListPage
      filters={{}}
      listings={listingsResponse}
      onFiltersChange={onFiltersChange}
    />,
  )

  expect(screen.getByText('Fiat Panda 1.0 FireFly Hybrid')).toBeVisible()
  expect(screen.getByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('Piemonte')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio annuncio' })).toHaveAttribute(
    'href',
    '/listings/30000000-0000-4000-8000-000000000001',
  )

  fireEvent.change(screen.getByLabelText('Model'), {
    target: { value: 'Panda' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Applica filtri' }))

  expect(onFiltersChange).toHaveBeenCalledWith({
    make: undefined,
    model: 'Panda',
    max_price_eur: undefined,
    max_mileage: undefined,
    location_region: undefined,
  })
})
