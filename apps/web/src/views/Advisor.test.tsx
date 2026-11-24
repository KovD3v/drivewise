import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type {
  AdvisorOffer,
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
            vehicle_type: 'car',
            generation_key: null,
            phase_key: null,
            catalog_version: 1,
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
            consumption_l_100km_basis: null,
            energy_consumption_kwh_100km: null,
            energy_consumption_kwh_100km_basis: null,
            wltp_range_km: null,
            co2_g_km: 113,
            euro_emission_standard: 'Euro 6e',
            seats: 4,
            cargo_volume_liters: 225,
            catalog_version: 1,
            powertrain_type: null,
            fuel: null,
            engine_code: null,
            valid_from: null,
            valid_to: null,
            external_references: [],
            provenance: [],
          },
          price_basis: 'offer',
          list_price: null,
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
              metric: null,
              value: null,
              threshold: null,
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
              source_license: null,
              observed_at: '2026-06-25',
              decision_id: null,
              observation_id: null,
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
  // Simulates a payload that breaks the contract, so the offer is loosened here.
  const offer: Record<string, unknown> = requireOffer(response.groups[0].items[0])
  offer.source_url = null
  delete offer.last_seen_at
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
    requireOffer(item).price_eur = priceEur
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
    ...requireOffer(item),
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
      ...requireOffer(item),
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

// The shared fixture item is an offer; tests that edit its offer read it here.
function requireOffer(item: AdvisorRecommendationItem): AdvisorOffer {
  if (!item.offer) {
    throw new Error('expected a fixture item priced by an offer')
  }
  return item.offer
}

// A variant with no eligible offer, ranked at its list price (ADR-013).
function listPriceItem(
  terms: Partial<NonNullable<AdvisorRecommendationItem['list_price']>> = {},
): AdvisorRecommendationItem {
  const item = structuredClone(recommendationResponse.groups[0].items[0])
  item.vehicle = { ...item.vehicle, make: 'Zephra', model: 'Tavo' }
  item.selected_spec = { ...item.selected_spec, consumption_l_100km_basis: 'interval_upper' }
  item.offer = null
  item.price_basis = 'list_price'
  item.list_price = {
    price_eur: 23450,
    computed_from_excl_vat: true,
    derivation: 'computed_from_excl_vat',
    printed_amount_eur: 19221.31,
    printed_basis: 'excl_vat',
    vat_rate_percent: 22,
    on_road_charge_eur: null,
    on_road_charge_includes_vat: null,
    trim_label: 'Tavo 1.2 Comfort',
    price_list_valid_from: '2026-09-01',
    substitute_note: 'Registered version is no longer listed.',
    source_name: 'Zephra price list (synthetic)',
    source_url: 'https://zephra.example.com/listino.pdf',
    source_license: 'Synthetic fixture only',
    observed_at: '2026-10-01T08:00:00Z',
    decision_id: '60000000-0000-4000-8000-000000000001',
    observation_id: '60000000-0000-4000-8000-000000000002',
    ...terms,
  }
  item.provenance = [
    {
      metric: 'list_price_eur',
      source_name: 'Zephra price list (synthetic)',
      source_url: 'https://zephra.example.com/listino.pdf',
      source_license: 'Synthetic fixture only',
      observed_at: '2026-10-01T08:00:00Z',
      decision_id: null,
      observation_id: null,
    },
    {
      metric: 'consumption_l_100km',
      source_name: 'Open emissions data (synthetic)',
      source_url: 'https://open-data.example.com/export',
      source_license: 'CC BY 4.0, credit the open dataset',
      observed_at: '2026-10-01T08:00:00Z',
      decision_id: null,
      observation_id: null,
    },
  ]
  return item
}

async function renderItems(items: AdvisorRecommendationItem[]) {
  const response = structuredClone(recommendationResponse)
  response.groups[0].items = items
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => response }),
  )
  renderWithRouter(<AdvisorPage />)
  fireEvent.change(screen.getByLabelText('Budget massimo'), {
    target: { value: '30000' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Trova veicoli' }))
  return screen.findAllByRole('article')
}

test('renders a list-price item with its terms, notes, document and credits', async () => {
  const [card] = await renderItems([listPriceItem()])
  const price = within(card).getByRole('region', { name: 'Prezzo di listino' })

  expect(within(price).getByText('Prezzo di listino')).toBeVisible()
  expect(within(price).getByText(/23.450/)).toBeVisible()
  expect(within(price).getByText('Tavo 1.2 Comfort')).toBeVisible()
  expect(within(price).getByText('01 set 2026')).toBeVisible()
  expect(within(price).getByText(/non un'offerta di un venditore/)).toBeVisible()
  expect(within(price).getByText(/abbiamo aggiunto l'IVA al 22%/)).toBeVisible()
  expect(within(price).getByText(/versione attuale più simile/)).toBeVisible()
  expect(within(price).getByRole('link', { name: 'Apri il listino' })).toHaveAttribute(
    'href',
    'https://zephra.example.com/listino.pdf',
  )
  // The raw note is data, not product copy: only the plain sentence is shown.
  expect(within(card).queryByText(/no longer listed/)).not.toBeInTheDocument()
  expect(within(card).getByText(/5 l\/100 km \(valore più alto dichiarato\)/)).toBeVisible()
  expect(within(card).getByText('Crediti delle fonti')).toBeVisible()
  expect(within(card).getByText('CC BY 4.0, credit the open dataset')).toBeVisible()
  expect(within(card).queryByText('Prezzo offerta')).not.toBeInTheDocument()
})

test('notes a turnkey list price and keeps offer cards free of list-price copy', async () => {
  const listed = listPriceItem({
    derivation: 'computed_from_turnkey',
    computed_from_excl_vat: false,
    printed_basis: 'turnkey',
    printed_amount_eur: 24400,
    on_road_charge_eur: 950,
    on_road_charge_includes_vat: true,
    substitute_note: null,
  })
  const [offerCard, listedCard] = await renderItems([
    structuredClone(recommendationResponse.groups[0].items[0]),
    listed,
  ])

  expect(within(listedCard).getByText(/chiavi in mano \(24.400/)).toBeVisible()
  expect(within(listedCard).queryByText(/versione attuale più simile/)).not.toBeInTheDocument()
  expect(within(offerCard).queryByText('Prezzo di listino')).not.toBeInTheDocument()
  expect(within(offerCard).queryByText(/valore più alto dichiarato/)).not.toBeInTheDocument()
  // The offer fixture's source has no licence, so no credits block appears.
  expect(within(offerCard).queryByText('Crediti delle fonti')).not.toBeInTheDocument()
})
