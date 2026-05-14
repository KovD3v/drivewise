import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { renderWithRouter } from '../test/renderWithRouter'
import { DocumentSearchPage } from './DocumentSearch'

const searchResponse = {
  query: 'fiat panda',
  mode: 'text_only',
  items: [
    {
      id: '40000000-0000-4000-8000-000000000001',
      title: 'Fiat Panda seed note',
      document_type: 'seed_note',
      score: 12.05,
      snippet: 'Synthetic Fiat Panda local fixture content.',
      metadata: {
        source_id: '10000000-0000-4000-8000-000000000010',
        vehicle_id: null,
        listing_id: null,
        created_at: '2026-01-15T00:00:00+00:00',
      },
      content: 'Full stored Fiat Panda document content.',
    },
  ],
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => searchResponse,
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('submits document search and renders text-only results', async () => {
  renderWithRouter(<DocumentSearchPage />)

  expect(screen.getByLabelText('Search mode')).toHaveValue('text_only')

  fireEvent.change(screen.getByLabelText('Query'), {
    target: { value: 'fiat panda' },
  })
  fireEvent.change(screen.getByLabelText('Document type'), {
    target: { value: 'seed_note' },
  })
  fireEvent.change(screen.getByLabelText('Limit'), {
    target: { value: '1' },
  })
  fireEvent.click(screen.getByLabelText('Include content'))
  fireEvent.click(screen.getByRole('button', { name: 'Search documents' }))

  expect(await screen.findByText('Fiat Panda seed note')).toBeVisible()
  expect(screen.getByText('mode: text_only')).toBeVisible()
  expect(screen.getByText('seed_note')).toBeVisible()
  expect(screen.getByText('Score 12.05')).toBeVisible()
  expect(screen.getByText('Synthetic Fiat Panda local fixture content.')).toBeVisible()
  expect(screen.getByText('source_id')).toBeVisible()
  expect(screen.getByText('Full stored Fiat Panda document content.')).toBeVisible()

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/search/documents',
      expect.objectContaining({
        body: JSON.stringify({
          query: 'fiat panda',
          document_type: 'seed_note',
          limit: 1,
          include_content: true,
          mode: 'text_only',
        }),
        method: 'POST',
      }),
    )
  })
})

test('submits vector fake search mode and shows dev warning', async () => {
  vi.mocked(fetch).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      query: 'fiat panda',
      mode: 'vector_fake',
      items: [],
    }),
  } as Response)

  renderWithRouter(<DocumentSearchPage />)

  fireEvent.change(screen.getByLabelText('Query'), {
    target: { value: 'fiat panda' },
  })
  fireEvent.change(screen.getByLabelText('Search mode'), {
    target: { value: 'vector_fake' },
  })

  expect(
    screen.getByText('Modalità dev: richiede embedding fake generati localmente.'),
  ).toBeVisible()

  fireEvent.click(screen.getByRole('button', { name: 'Search documents' }))

  expect(await screen.findByText('mode: vector_fake')).toBeVisible()
  expect(
    screen.getByText('Nessun documento con embedding o nessun risultato.'),
  ).toBeVisible()

  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/search/documents',
      expect.objectContaining({
        body: JSON.stringify({
          query: 'fiat panda',
          limit: 10,
          include_content: false,
          mode: 'vector_fake',
        }),
        method: 'POST',
      }),
    )
  })
})
