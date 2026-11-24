import { afterEach, expect, test, vi } from 'vitest'

import { analyzeModel, fetchVehicle, fetchVehicles, isApiNotFoundError, resolveApiBaseUrl } from './drivewise'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

test('surfaces HTTP failures with the API detail', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Catalog unavailable' }),
    }),
  )

  await expect(fetchVehicles()).rejects.toThrow('Catalog unavailable')
})

test('surfaces network failures instead of inventing data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

  await expect(fetchVehicles()).rejects.toThrow('Failed to fetch')
})

test('asks the API for one vehicle type', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))

  await fetchVehicles({ vehicle_type: 'scooter', limit: 100, offset: 0 })

  expect(fetch).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/vehicles?vehicle_type=scooter&limit=100&offset=0',
  )
})

test('identifies missing API records as not found errors', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Vehicle not found' }),
    }),
  )

  const error = await fetchVehicle('missing').catch((caughtError) => caughtError)

  expect(isApiNotFoundError(error)).toBe(true)
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

test('a one-origin build sends browser requests to /api, never to the local API', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '/api')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))
  await fetchVehicles({ vehicle_type: 'car' })
  expect(fetch).toHaveBeenCalledWith('/api/vehicles?vehicle_type=car')
  expect(resolveApiBaseUrl({ ssr: false, publicUrl: '/api' })).toBe('/api')
})

test('server rendering uses API_INTERNAL_URL and refuses a relative base without it', () => {
  expect(resolveApiBaseUrl({ ssr: true, internalUrl: 'http://api.internal/api/', publicUrl: '/api' })).toBe('http://api.internal/api')
  expect(() => resolveApiBaseUrl({ ssr: true, publicUrl: '/api' })).toThrow('API_INTERNAL_URL')
  expect(resolveApiBaseUrl({ ssr: true, publicUrl: 'http://127.0.0.1:8047' })).toBe('http://127.0.0.1:8047')
})
