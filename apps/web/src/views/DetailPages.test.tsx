import { screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'

import {
  mockDocumentDetails,
  mockListings,
  mockVehicleDetails,
} from '../api/mockData'
import { renderWithRouter } from '../test/renderWithRouter'
import { DocumentDetailPage } from './DocumentDetail'
import { ListingDetailPage } from './ListingDetail'
import { VehicleDetailPage } from './VehicleDetail'

test('renders vehicle detail loader data', () => {
  renderWithRouter(<VehicleDetailPage vehicle={mockVehicleDetails[0]} />)

  expect(screen.getByRole('heading', { name: 'Fiat Panda' })).toBeVisible()
  expect(screen.getByText('1.0 FireFly Hybrid')).toBeVisible()
  expect(screen.getByText('70 CV')).toBeVisible()
})

test('renders listing detail loader data and its vehicle link', () => {
  renderWithRouter(<ListingDetailPage listing={mockListings[0]} />)

  expect(
    screen.getByRole('heading', { name: 'Fiat Panda 1.0 FireFly Hybrid' }),
  ).toBeVisible()
  expect(screen.getByText('Piemonte')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio veicolo' })).toHaveAttribute(
    'href',
    `/vehicles/${mockListings[0].vehicle.id}`,
  )
})

test('renders document detail loader data without embedding metadata', () => {
  const document = {
    ...mockDocumentDetails[0],
    metadata: {
      ...mockDocumentDetails[0].metadata,
      embedding: [0.1, 0.2],
      nested: { embedding_model: 'private-model', visible: true },
    },
  }
  renderWithRouter(<DocumentDetailPage document={document} />)

  expect(
    screen.getByRole('heading', { name: 'Synthetic profile: Fiat Panda' }),
  ).toBeVisible()
  expect(screen.getByText(/compact Italian city car/)).toBeVisible()
  expect(screen.getByText(/"visible": true/)).toBeVisible()
  expect(screen.queryByText(/private-model/)).not.toBeInTheDocument()
  expect(screen.queryByText(/"embedding"/)).not.toBeInTheDocument()
})

test('renders unknown catalog v2 identity fields without inventing values', () => {
  const vehicle = {
    ...mockVehicleDetails[0],
    model_year: null,
    body_style: null,
    fuel_type: null,
    specs: [{ ...mockVehicleDetails[0].specs[0], trim: null }],
  }
  renderWithRouter(<VehicleDetailPage vehicle={vehicle} />)
  expect(screen.getByText(/Anno non disponibile/)).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Allestimento non disponibile' })).toBeVisible()
})

test('renders a catalogue list price, an interval consumption and source credits', () => {
  const base = mockVehicleDetails[0]
  const spec = {
    ...base.specs[0],
    consumption_l_100km: 6.1,
    consumption_l_100km_basis: 'interval_upper' as const,
    list_price: {
      price_eur: 30500,
      computed_from_excl_vat: false,
      derivation: 'computed_from_turnkey' as const,
      printed_amount_eur: 31720,
      printed_basis: 'turnkey' as const,
      vat_rate_percent: null,
      on_road_charge_eur: 1220,
      on_road_charge_includes_vat: true,
      trim_label: 'Tavo E Comfort',
      price_list_valid_from: '2026-09-01',
      substitute_note: 'Registered version is no longer listed.',
      source_name: 'Zephra price list (synthetic)',
      source_url: 'https://zephra.example.com/listino.pdf',
      source_license: 'Synthetic fixture only',
      observed_at: '2026-10-01T08:00:00Z',
      decision_id: '60000000-0000-4000-8000-000000000001',
      observation_id: '60000000-0000-4000-8000-000000000002',
    },
    provenance: [
      {
        source_id: '70000000-0000-4000-8000-000000000001',
        source_key: 'open-data',
        source_name: 'Open emissions data (synthetic)',
        source_url: 'https://open-data.example.com/export',
        source_license: 'CC BY 4.0, credit the open dataset',
        observed_at: '2026-10-01T08:00:00Z',
        record_observed_at: '2026-10-01T08:00:00Z',
        content_hash: 'a'.repeat(64),
        is_current: true,
        supported_metrics: ['consumption_l_100km'],
      },
    ],
  }
  renderWithRouter(<VehicleDetailPage vehicle={{ ...base, specs: [spec] }} />)

  const price = screen.getByRole('region', { name: 'Prezzo di listino' })
  expect(within(price).getByText('Tavo E Comfort')).toBeVisible()
  expect(within(price).getByText('01 set 2026')).toBeVisible()
  expect(within(price).getByText(/chiavi in mano \(31.720/)).toBeVisible()
  expect(within(price).getByText(/versione attuale più simile/)).toBeVisible()
  expect(within(price).getByRole('link', { name: 'Apri il listino' })).toHaveAttribute(
    'href',
    'https://zephra.example.com/listino.pdf',
  )
  expect(screen.getByText('6.1 l/100km (valore più alto dichiarato)')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Open emissions data (synthetic)' })).toHaveAttribute(
    'href',
    'https://open-data.example.com/export',
  )
  expect(screen.getByText('CC BY 4.0, credit the open dataset')).toBeVisible()
})

test('shows no list-price block for a spec without catalogue terms', () => {
  renderWithRouter(<VehicleDetailPage vehicle={mockVehicleDetails[0]} />)
  expect(screen.queryByRole('region', { name: 'Prezzo di listino' })).not.toBeInTheDocument()
  expect(screen.queryByText('Crediti delle fonti')).not.toBeInTheDocument()
})
