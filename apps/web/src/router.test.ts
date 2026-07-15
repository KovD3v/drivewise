import { createMemoryHistory, createRouter } from '@tanstack/react-router'
import { afterEach, expect, test, vi } from 'vitest'

import { routeTree } from './routeTree.gen'

afterEach(() => {
  vi.unstubAllGlobals()
})

test.each([
  ['/vehicles/vehicle-1', '/vehicles'],
  ['/listings/listing-1', '/listings'],
  ['/documents/document-1', '/documents'],
])('matches %s without rendering the collection route', async (path, collectionRouteId) => {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
  })

  await router.load()

  expect(router.state.matches.map((match) => match.routeId)).not.toContain(
    collectionRouteId,
  )
})

test.each([
  ['/vehicles', 'http://127.0.0.1:8000/vehicles'],
  ['/listings', 'http://127.0.0.1:8000/listings'],
  ['/documents', 'http://127.0.0.1:8000/documents'],
])('loads initial collection data for %s', async (path, apiUrl) => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    }),
  )
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
  })

  await router.load()

  expect(fetch).toHaveBeenCalledWith(apiUrl)
})
