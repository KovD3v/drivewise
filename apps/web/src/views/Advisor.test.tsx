import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type {
  AdvisorRecommendationItem,
  AdvisorRecommendationResponse,
} from '../api/drivewise'
import { renderWithRouter } from '../test/renderWithRouter'
import { AdvisorPage } from './Advisor'

const recommendationResponse: AdvisorRecommendationResponse = {
  run_id: '50000000-0000-4000-8000-000000000001',
  scoring_version: 'advisor-v3.0',
  assumptions: ['14.000 km annui', 'Prezzi energia aggiornati a luglio 2026'],
  excluded_counts_by_reason: {
    stale_offer: 2,
    over_budget_limit: 1,
  },
  insufficient_data_counts_by_reason: {},
  groups: [
    {
      condition: 'new',
      items: [
        {
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
          selected_spec: {
            id: '20000000-0000-4000-8000-000000000001',
            variant_key: 'fiat-panda-2024-firefly-hybrid',
            is_default: true,
            trim: '1.0 FireFly Hybrid',
            body_style: 'city_car',
            fuel_type: 'mild_hybrid_petrol',
            list_price_eur: 15500,
            drivetrain: 'fwd',
            transmission: '6-speed manual',
            engine: '1.0L mild-hybrid petrol',
            horsepower: 70,
            battery_kwh: null,
            consumption_l_100km: 5,
            energy_consumption_kwh_100km: null,
            wltp_range_km: null,
            co2_g_km: 113,
            euro_emission_standard: 'Euro 6e',
            seats: 4,
            cargo_volume_liters: 225,
          },
          offer: {
            id: '30000000-0000-4000-8000-000000000001',
            vehicle_id: '00000000-0000-4000-8000-000000000001',
            spec_id: '20000000-0000-4000-8000-000000000001',
            source_id: '10000000-0000-4000-8000-000000000001',
            listing_ref: 'reviewed-fiat-panda-2024-it',
            title: 'Fiat Panda 1.0 FireFly Hybrid',
            price_eur: 15800,
            mileage: 0,
            condition: 'new',
            location_region: 'Piemonte',
            source_url: 'https://example.com/offers/panda',
            listed_at: '2026-07-10',
            last_seen_at: '2026-07-15T10:00:00Z',
            valid_until: '2026-08-15',
            is_active: true,
          },
          score: 91.4,
          decision_status: 'complete',
          decision_score: 91.4,
          decision_confidence: 88.2,
          structural_fit: 90,
          preference_fit: 94,
          pillar_scores: {
            economics: 90,
            practicality: 88,
          },
          penalties: [],
          strengths: ['economics'],
          missing_factors: [],
          warnings: [],
          module_versions: { scoring: 'advisor-v3.0' },
          assumptions: [],
          score_composition: {
            structural_fit_weight: 65,
            preference_fit_weight: 35,
          },
          component_scores: {
            price_fit: 95,
            use_case_fit: 100,
            running_cost: 82,
            space: 74,
            efficiency_range: 80,
          },
          positive_factors: [
            {
              component: 'use_case_fit',
              message: "La carrozzeria e adatta all'uso urbano.",
              metric: 'body_style',
              value: 'city_car',
              threshold: 'city_car',
              contribution: 25,
            },
          ],
          tradeoffs: [
            {
              component: 'space',
              message: 'Il bagagliaio e sotto la fascia piu versatile.',
              contribution: 11.1,
            },
          ],
          evidence: {
            annual_km: 14000,
            annual_energy_cost_eur: 1295,
            consumption_l_100km: 5,
            cargo_volume_liters: 225,
          },
          provenance: [
            {
              metric: 'consumption_l_100km',
              source_name: 'EEA passenger-car data',
              source_url: 'https://example.com/eea',
              observed_at: '2026-06-25',
            },
          ],
        },
      ],
    },
    {
      condition: 'used',
      items: [],
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

test('submits Advisor preferences and renders transparent condition groups', async () => {
  renderWithRouter(<AdvisorPage />)

  expect(screen.getByRole('option', { name: 'Ibrido benzina' })).toHaveValue(
    'hybrid_petrol',
  )
  expect(
    screen.getByRole('option', { name: 'Full hybrid benzina' }),
  ).toHaveValue('full_hybrid_petrol')
  expect(screen.getByRole('option', { name: 'Compatta' })).toHaveValue(
    'small_hatchback',
  )
  expect(screen.getByRole('option', { name: 'Crossover' })).toHaveValue(
    'crossover',
  )

  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.change(screen.getByLabelText('Condizione'), {
    target: { value: 'any' },
  })
  fireEvent.change(screen.getByLabelText('Km annui'), {
    target: { value: '14000' },
  })
  fireEvent.change(screen.getByLabelText('Alimentazione preferita'), {
    target: { value: 'mild_hybrid_petrol' },
  })
  fireEvent.change(screen.getByLabelText('Carrozzeria preferita'), {
    target: { value: 'city_car' },
  })
  fireEvent.click(screen.getByLabelText('Prezzo'))
  fireEvent.click(screen.getByLabelText('Efficienza e autonomia'))
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(
    await screen.findByRole('heading', { name: 'Fiat Panda' }),
  ).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Nuovo' })).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Usato' })).toBeVisible()
  expect(screen.getByText('1.0 FireFly Hybrid')).toBeVisible()
  expect(screen.getByText('Punti forti')).toBeVisible()
  expect(screen.getByText('Compromessi')).toBeVisible()
  expect(screen.getByText("La carrozzeria e adatta all'uso urbano.")).toBeVisible()
  expect(
    screen.getByText('Il bagagliaio e sotto la fascia piu versatile.'),
  ).toBeVisible()
  expect(screen.getByText('EEA passenger-car data')).toHaveAttribute(
    'href',
    'https://example.com/eea',
  )
  expect(
    screen.getByRole('link', { name: "Apri la fonte dell'offerta" }),
  ).toHaveAttribute('href', 'https://example.com/offers/panda')
  expect(screen.getByText(/Nessuna offerta usata soddisfa/)).toBeVisible()
  expect(screen.getByText('14.000 km annui')).toBeVisible()
  expect(screen.getByText('Scoring advisor-v3.0')).toBeVisible()
  expect(screen.getByText('Decision Score')).toBeVisible()
  expect(screen.queryByText('Evidence documentale')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Affidabilita')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Sicurezza')).not.toBeInTheDocument()

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/advisor/recommendations',
      expect.objectContaining({
        body: JSON.stringify({
          budget_max_eur: 20000,
          primary_use: 'city',
          condition: 'any',
          annual_km: 14000,
          preferred_fuel_type: 'mild_hybrid_petrol',
          preferred_body_style: 'city_car',
          priorities: ['price', 'efficiency_range'],
        }),
        method: 'POST',
      }),
    )
  })
})

test('labels an insufficient-data recommendation as provisional Structural Fit', async () => {
  const response = structuredClone(recommendationResponse)
  const item = response.groups[0].items[0]
  item.decision_status = 'insufficient_data'
  item.decision_score = null
  item.score = 72
  item.missing_factors = ['powertrain_fit']
  item.warnings = ['vehicle.wltp_range_km']
  response.insufficient_data_counts_by_reason = { powertrain_fit: 1 }
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
  )

  renderWithRouter(<AdvisorPage />)

  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(await screen.findByText('Structural Fit provvisorio')).toBeVisible()
  expect(screen.getByText(/Risultato provvisorio/)).toBeVisible()
  expect(screen.getAllByText(/powertrain fit/).length).toBeGreaterThan(0)
  expect(screen.queryByText('Decision Score')).not.toBeInTheDocument()
})

test('renders a recommendation defensively without provenance or a source URL', async () => {
  const response = structuredClone(recommendationResponse)
  response.groups[0].items[0].provenance = []
  response.groups[0].items[0].offer.source_url = null
  delete response.groups[0].items[0].offer.last_seen_at
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
  )

  renderWithRouter(<AdvisorPage />)
  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(await screen.findByText('URL fonte non disponibile')).toBeVisible()
  expect(screen.queryByText('Fonti dei dati')).not.toBeInTheDocument()
  expect(screen.getByText('10 lug 2026')).toBeVisible()
})

test('disables and omits used-only mileage for new-vehicle requests', async () => {
  renderWithRouter(<AdvisorPage />)

  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '20000' },
  })
  fireEvent.change(screen.getByLabelText('Chilometraggio massimo usato'), {
    target: { value: '30000' },
  })
  fireEvent.change(screen.getByLabelText('Condizione'), {
    target: { value: 'new' },
  })

  expect(screen.getByLabelText('Chilometraggio massimo usato')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  await waitFor(() => {
    const [, request] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse(String(request?.body))
    expect(body.condition).toBe('new')
    expect(body).not.toHaveProperty('max_mileage')
  })
})

test('submits used constraints and renders a certified EV recommendation', async () => {
  const response = structuredClone(recommendationResponse)
  response.groups = [
    {
      condition: 'used',
      items: [certifiedElectricItem()],
    },
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
  )

  renderWithRouter(<AdvisorPage />)
  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '25000' },
  })
  fireEvent.change(screen.getByLabelText('Condizione'), {
    target: { value: 'used' },
  })
  fireEvent.change(screen.getByLabelText('Km annui'), {
    target: { value: '18000' },
  })
  fireEvent.change(screen.getByLabelText('Chilometraggio massimo usato'), {
    target: { value: '30000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  expect(
    await screen.findByRole('heading', { name: 'Tesla Model 3' }),
  ).toBeVisible()
  expect(screen.getByText('Usato certificato')).toBeVisible()
  expect(screen.getByText('15,5 kWh/100 km')).toBeVisible()
  expect(screen.getByText('310 km')).toBeVisible()

  await waitFor(() => {
    const [, request] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(String(request?.body))).toEqual({
      budget_max_eur: 25000,
      primary_use: 'city',
      condition: 'used',
      annual_km: 18000,
      max_mileage: 30000,
      priorities: [],
    })
  })
})

test('renders at most five recommendations in each populated condition group', async () => {
  const response = structuredClone(recommendationResponse)
  response.groups = [
    {
      condition: 'new',
      items: recommendationItems('new', 6),
    },
    {
      condition: 'used',
      items: recommendationItems('used', 6),
    },
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
  )

  renderWithRouter(<AdvisorPage />)
  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '25000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

  const newGroup = await screen.findByRole('region', { name: 'Nuovo' })
  const usedGroup = screen.getByRole('region', { name: 'Usato' })
  expect(within(newGroup).getAllByRole('article')).toHaveLength(5)
  expect(within(usedGroup).getAllByRole('article')).toHaveLength(5)
  expect(
    screen.queryByRole('heading', { name: 'New model 6' }),
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole('heading', { name: 'Used model 6' }),
  ).not.toBeInTheDocument()
})

test.each([
  {
    overrunEur: 500,
    overrunPercent: 5,
    priceEur: 10500,
    message: 'Il prezzo supera il budget massimo di EUR 500.00 (5.00%).',
  },
  {
    overrunEur: 1000,
    overrunPercent: 10,
    priceEur: 11000,
    message: 'Il prezzo supera il budget massimo di EUR 1000.00 (10.00%).',
  },
])(
  'renders the exact $overrunPercent% server-provided budget overrun',
  async ({ message, overrunEur, overrunPercent, priceEur }) => {
    const response = structuredClone(recommendationResponse)
    const item = response.groups[0].items[0]
    item.offer.price_eur = priceEur
    item.evidence = {
      ...item.evidence,
      budget_max_eur: 10000,
      budget_overrun_eur: overrunEur,
      budget_overrun_percent: overrunPercent,
      price_eur: priceEur,
    }
    item.tradeoffs = [
      {
        component: 'price_fit',
        message,
        metric: 'budget_overrun_eur',
        value: overrunEur,
        threshold: 10000,
        contribution: 8.4,
      },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
    )

    renderWithRouter(<AdvisorPage />)
    fireEvent.change(screen.getByLabelText('Budget massimo'), {
      target: { value: '10000' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))

    expect(await screen.findByText(message)).toBeVisible()
  },
)

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

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Database unavailable',
  )
})

function certifiedElectricItem(): AdvisorRecommendationItem {
  const item = structuredClone(recommendationResponse.groups[0].items[0])
  item.vehicle = {
    ...item.vehicle,
    id: '00000000-0000-4000-8000-000000000005',
    canonical_key: 'it-tesla-model-3-2026',
    model_family_key: 'it-tesla-model-3',
    make: 'Tesla',
    model: 'Model 3',
    body_style: 'sedan',
    fuel_type: 'electric',
    base_price_eur: 42990,
  }
  item.selected_spec = {
    ...item.selected_spec,
    id: '20000000-0000-4000-8000-000000000005',
    variant_key: 'it-tesla-model-3-2026-rwd',
    trim: 'Rear-Wheel Drive',
    body_style: 'sedan',
    fuel_type: 'electric',
    list_price_eur: 42990,
    engine: 'single electric motor',
    transmission: 'single-speed',
    battery_kwh: 48,
    consumption_l_100km: null,
    energy_consumption_kwh_100km: 15.5,
    wltp_range_km: 310,
    co2_g_km: 0,
    cargo_volume_liters: 594,
  }
  item.offer = {
    ...item.offer,
    id: '30000000-0000-4000-8000-000000000005',
    vehicle_id: item.vehicle.id,
    spec_id: item.selected_spec.id,
    listing_ref: 'reviewed-tesla-model-3-certified',
    title: 'Tesla Model 3 RWD certificata',
    price_eur: 22000,
    mileage: 12000,
    condition: 'certified',
    location_region: 'Lombardia',
    source_url: 'https://example.com/offers/model-3',
  }
  item.evidence = {
    annual_km: 18000,
    annual_energy_cost_eur: 825,
    energy_consumption_kwh_100km: 15.5,
    wltp_range_km: 310,
    cargo_volume_liters: 594,
  }
  return item
}

function recommendationItems(
  condition: 'new' | 'used',
  count: number,
): AdvisorRecommendationItem[] {
  return Array.from({ length: count }, (_, index) => {
    const item = structuredClone(recommendationResponse.groups[0].items[0])
    const position = index + 1
    const label = condition === 'new' ? 'New' : 'Used'
    item.vehicle = {
      ...item.vehicle,
      id: `${condition}-vehicle-${position}`,
      canonical_key: `${condition}-vehicle-${position}`,
      model_family_key: `${condition}-family-${position}`,
      make: label,
      model: `model ${position}`,
    }
    item.selected_spec = {
      ...item.selected_spec,
      id: `${condition}-spec-${position}`,
      variant_key: `${condition}-variant-${position}`,
    }
    item.offer = {
      ...item.offer,
      id: `${condition}-offer-${position}`,
      vehicle_id: item.vehicle.id,
      spec_id: item.selected_spec.id,
      listing_ref: `${condition}-listing-${position}`,
      condition,
      mileage: condition === 'new' ? 0 : position * 1000,
    }
    return item
  })
}
