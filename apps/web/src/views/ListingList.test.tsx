import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, test, expect, vi } from 'vitest'

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

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => listingsResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders loader data before fetching filtered listings', async () => {
  renderWithRouter(<ListingListPage initialListings={listingsResponse} />)

  expect(screen.getByText('Fiat Panda 1.0 FireFly Hybrid')).toBeVisible()
  expect(screen.getByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('Piemonte')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio annuncio' })).toHaveAttribute(
    'href',
    '/listings/30000000-0000-4000-8000-000000000001',
  )

  expect(fetch).not.toHaveBeenCalled()

  fireEvent.change(screen.getByLabelText('Model'), {
    target: { value: 'Panda' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Applica filtri' }))

  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/listings?model=Panda',
    ),
  )
})
