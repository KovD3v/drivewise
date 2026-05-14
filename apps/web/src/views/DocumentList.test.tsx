import { screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { DocumentListPage } from './DocumentList'

const documentsResponse = [
  {
    id: '40000000-0000-4000-8000-000000000001',
    source_id: '10000000-0000-4000-8000-000000000010',
    vehicle_id: null,
    listing_id: null,
    document_type: 'listing_snapshot',
    title: 'Fiat Panda local listing',
    content: 'Fiat Panda in Piemonte, prezzo 14200 EUR, 6400 km.',
    metadata: {
      content_hash: 'hash-fiat-panda',
      local_path: 'data/fixtures/ingestion/fiat-panda-listing.txt',
      proposed_vehicle: {
        make: 'Fiat',
        model: 'Panda',
      },
      proposed_listing: {
        price_eur: 14200,
        mileage: 6400,
      },
      unparsed_fields: {},
    },
    created_at: '2026-01-15T00:00:00Z',
  },
]

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => documentsResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders document list from the API', async () => {
  renderWithRouter(<DocumentListPage />)

  expect(await screen.findByText('Fiat Panda local listing')).toBeVisible()
  expect(screen.getByText('listing_snapshot')).toBeVisible()
  expect(
    screen.getByText('data/fixtures/ingestion/fiat-panda-listing.txt'),
  ).toBeVisible()
  expect(screen.getByText('Fiat Panda')).toBeVisible()
  expect(screen.getByText('price_eur: 14200')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio documento' })).toHaveAttribute(
    'href',
    '/documents/40000000-0000-4000-8000-000000000001',
  )

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/documents')
  })
})
