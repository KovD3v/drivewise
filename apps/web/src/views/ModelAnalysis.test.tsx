import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { ModelAnalysisPage } from './ModelAnalysis'

const analysisResponse = {
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
  resolved_spec: {
    id: '20000000-0000-4000-8000-000000000001',
    trim: '1.0 FireFly Hybrid',
    drivetrain: 'fwd',
    transmission: '6-speed manual',
    engine: '1.0L mild-hybrid petrol',
    horsepower: 70,
    battery_kwh: null,
    consumption_l_100km: 5,
    wltp_range_km: null,
    co2_g_km: 113,
    euro_emission_standard: 'Euro 6e',
    seats: 4,
    cargo_volume_liters: 225,
  },
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
  checklist: ['verify_service_history', 'inspect_brakes_and_tires'],
  confidence: 0.86,
  assumptions: ['No live market sources are used in Model Analysis V1.'],
  warnings: [],
  missing_data: [],
  next_actions: ['modify_parameters', 'open_checklist', 'compare_alternatives'],
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => analysisResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('submits a model analysis request and renders the result contract', async () => {
  renderWithRouter(<ModelAnalysisPage />)

  fireEvent.change(screen.getByLabelText('Modello'), {
    target: { value: 'fiat panda 1.0 firefly hybrid 2024' },
  })
  fireEvent.change(screen.getByLabelText('Prezzo richiesto'), {
    target: { value: '14500' },
  })
  fireEvent.change(screen.getByLabelText('Km attuali'), {
    target: { value: '6400' },
  })
  fireEvent.click(screen.getByLabelText('City'))
  fireEvent.click(screen.getByLabelText('Mixed'))
  fireEvent.click(screen.getByRole('button', { name: 'Analizza modello' }))

  expect(await screen.findByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('Interessante, con verifiche consigliate')).toBeVisible()
  expect(screen.getByText('In linea con il mercato')).toBeVisible()
  expect(screen.getByText('Affidabilità 86%')).toBeVisible()
  expect(screen.getByText('Verifica lo storico della manutenzione')).toBeVisible()
  expect(
    screen.getByText('L’analisi V1 non usa fonti di mercato in tempo reale.'),
  ).toBeVisible()
  expect(screen.getByText('Modifica parametri')).toBeVisible()
  expect(screen.getByText('Apri checklist')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Modifica parametri' })).toBeNull()

  await waitFor(() => {
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
})

test('shows an error when model analysis fails', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Database connection failed.' }),
    }),
  )

  renderWithRouter(<ModelAnalysisPage />)

  fireEvent.change(screen.getByLabelText('Modello'), {
    target: { value: 'fiat panda' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Analizza modello' }))

  expect(await screen.findByText('Database connection failed.')).toBeVisible()
})
