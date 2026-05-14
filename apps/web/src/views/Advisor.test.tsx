import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, test, expect, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { AdvisorPage } from './Advisor'

const recommendationResponse = {
  run_id: '50000000-0000-4000-8000-000000000001',
  items: [
    {
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
      best_listing: {
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
      },
      score: 104.25,
      rationale: 'Price fits the requested budget. City-car body style fits urban use.',
      evidence: {
        within_budget: true,
        price_eur: 14200,
        budget_max_eur: 20000,
        consumption_l_100km: 5,
        co2_g_km: 113,
        seats: 4,
        cargo_volume_liters: 225,
        missing_fields: [],
      },
      document_evidence: [
        {
          document_id: '40000000-0000-4000-8000-000000000001',
          title: 'Fiat Panda local profile',
          document_type: 'vehicle_profile',
          score: 18.05,
          snippet: 'Fiat Panda compact city-car evidence from local ingestion.',
        },
      ],
    },
  ],
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => recommendationResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('submits advisor preferences and renders recommendation results', async () => {
  renderWithRouter(<AdvisorPage />)

  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.change(screen.getByLabelText('Uso principale'), {
    target: { value: 'city' },
  })
  fireEvent.click(screen.getByLabelText('Prezzo'))
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(await screen.findByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('Score 104.25')).toBeVisible()
  expect(screen.getByText('Piemonte')).toBeVisible()
  expect(screen.getByText('Fiat Panda local profile')).toBeVisible()
  expect(
    screen.getByText('Fiat Panda compact city-car evidence from local ingestion.'),
  ).toBeVisible()
  expect(screen.getByRole('link', { name: 'Apri documento evidence' })).toHaveAttribute(
    'href',
    '/documents/40000000-0000-4000-8000-000000000001',
  )

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/advisor/recommendations',
      expect.objectContaining({
        method: 'POST',
      }),
    )
  })
})

test('shows an error when advisor request fails', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Database unavailable' }),
    }),
  )

  renderWithRouter(<AdvisorPage />)

  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(await screen.findByText('Database unavailable')).toBeVisible()
})
