import { afterEach, expect, test, vi } from 'vitest'

import {
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
