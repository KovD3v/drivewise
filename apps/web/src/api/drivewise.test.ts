import { afterEach, expect, test, vi } from 'vitest'

import {
  analyzeModel,
  fetchDocuments,
  fetchListings,
  fetchVehicles,
  searchDocuments,
} from './drivewise'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

test('does not fall back to mock data unless VITE_USE_MOCK_API is enabled', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(fetchVehicles()).rejects.toThrow('Failed to fetch')
})

test('uses mock data when VITE_USE_MOCK_API is enabled', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'true')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(fetchVehicles()).resolves.toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        make: 'Fiat',
        model: 'Panda',
      }),
    ]),
  )
})

test('uses mock document search only when VITE_USE_MOCK_API is enabled', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'true')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(
    searchDocuments({ query: 'fiat panda', include_content: true }),
  ).resolves.toEqual(
    expect.objectContaining({
      mode: 'text_only',
      items: expect.arrayContaining([
        expect.objectContaining({
          title: 'Fiat Panda local listing',
          content: expect.stringContaining('Fiat Panda'),
        }),
      ]),
    }),
  )
})

test('mock search normalizes query and mirrors backend text-only scoring', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'true')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(
    searchDocuments({ query: ' fiat    panda ', document_type: 'seed_note' }),
  ).resolves.toEqual(
    expect.objectContaining({
      query: 'fiat panda',
      items: [
        expect.objectContaining({
          title: 'Synthetic profile: Fiat Panda',
          score: 12.05,
          snippet: 'Synthetic profile: Fiat Panda',
        }),
      ],
    }),
  )
})

test('mock search supports vector fake mode', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'true')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(
    searchDocuments({ query: 'fiat panda', mode: 'vector_fake' }),
  ).resolves.toEqual(
    expect.objectContaining({
      query: 'fiat panda',
      mode: 'vector_fake',
      items: expect.any(Array),
    }),
  )
})

test('mock collection filters include backend id filters', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'true')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Failed to fetch')))

  await expect(
    fetchListings({ vehicle_id: '00000000-0000-4000-8000-000000000004' }),
  ).resolves.toEqual([
    expect.objectContaining({
      title: 'Dacia Sandero Eco-G 100',
    }),
  ])

  await expect(
    fetchDocuments({
      source_id: '10000000-0000-4000-8000-000000000001',
      vehicle_id: '00000000-0000-4000-8000-000000000001',
      listing_id: '30000000-0000-4000-8000-000000000001',
      q: 'compact',
      document_type: 'seed_note',
    }),
  ).resolves.toEqual([
    expect.objectContaining({
      title: 'Synthetic profile: Fiat Panda',
    }),
  ])
})

test('posts model analysis requests to the advisor endpoint', async () => {
  const modelAnalysisResponse = {
    status: 'completed',
    resolved_vehicle: {
      id: '00000000-0000-4000-8000-000000000001',
      make: 'Fiat',
      model: 'Panda',
      model_year: 2024,
      body_style: 'city_car',
      fuel_type: 'mild_hybrid_petrol',
      market: 'IT',
      base_price_eur: 15500,
    },
    resolved_spec: null,
    verdict: 'interesting_with_checks',
    price_assessment: 'in_range',
    estimated_costs: {
      market_reference_price_eur: 14200,
      estimated_annual_maintenance_eur: 576,
      estimated_monthly_energy_eur: 92.5,
      estimated_depreciation_3y_eur: 4060,
      notes: ['annual_km_assumption:12000'],
    },
    red_flags: [],
    checklist: ['verify_service_history'],
    confidence: 0.86,
    assumptions: ['No live market sources are used in Model Analysis V1.'],
    warnings: [],
    missing_data: [],
    next_actions: ['modify_parameters', 'open_checklist', 'compare_alternatives'],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => modelAnalysisResponse,
    }),
  )

  await expect(
    analyzeModel({
      query: 'fiat panda 1.0 firefly hybrid 2024',
      market: 'IT',
      asking_price_eur: 14500,
      current_km: 6400,
      usage_profile: ['city', 'mixed'],
      analysis_scope: ['price', 'maintenance', 'red_flags', 'tco'],
    }),
  ).resolves.toEqual(modelAnalysisResponse)

  expect(fetch).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/advisor/model-analysis',
    expect.objectContaining({
      body: JSON.stringify({
        query: 'fiat panda 1.0 firefly hybrid 2024',
        market: 'IT',
        asking_price_eur: 14500,
        current_km: 6400,
        usage_profile: ['city', 'mixed'],
        analysis_scope: ['price', 'maintenance', 'red_flags', 'tco'],
      }),
      method: 'POST',
    }),
  )
})
