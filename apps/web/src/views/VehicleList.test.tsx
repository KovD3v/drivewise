import { screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, test, expect, vi } from 'vitest'

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

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => vehiclesResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders vehicle list from the API', async () => {
  renderWithRouter(<VehicleListPage />)

  expect(await screen.findByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('2024 · city_car')).toBeVisible()
  expect(screen.getByText('mild_hybrid_petrol')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio veicolo' })).toHaveAttribute(
    'href',
    '/vehicles/00000000-0000-4000-8000-000000000001',
  )

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/vehicles')
  })
})
