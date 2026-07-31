import { createElement } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router'
import { afterEach, expect, test, vi } from 'vitest'

import { mockListings, mockVehicleDetails } from './api/mockData'
import { routeTree } from './routeTree.gen'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

test.each([
  [
    '/vehicles/vehicle-1',
    '/vehicles',
    'http://127.0.0.1:8000/vehicles/vehicle-1',
  ],
  [
    '/listings/listing-1',
    '/listings',
    'http://127.0.0.1:8000/listings/listing-1',
  ],
  [
    '/documents/document-1',
    '/documents',
    'http://127.0.0.1:8000/documents/document-1',
  ],
])(
  'loads %s without rendering the collection route',
  async (path, collectionRouteId, apiUrl) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({}),
      }),
    )
    const router = createRouter({
      routeTree,
      history: createMemoryHistory({ initialEntries: [path] }),
    })

    await router.load()

    expect(router.state.matches.map((match) => match.routeId)).not.toContain(
      collectionRouteId,
    )
    expect(fetch).toHaveBeenCalledWith(apiUrl)
  },
)

test.each([
  ['/vehicles', 'http://127.0.0.1:8000/vehicles'],
  ['/vehicles?make=tes', 'http://127.0.0.1:8000/vehicles?make=tes'],
  ['/listings', 'http://127.0.0.1:8000/listings'],
  ['/listings?model=Panda', 'http://127.0.0.1:8000/listings?model=Panda'],
  ['/documents', 'http://127.0.0.1:8000/documents'],
  [
    '/documents?q=Fiat+Panda',
    'http://127.0.0.1:8000/documents?q=Fiat+Panda',
  ],
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

test('renders successful detail loader data through the real route tree', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockVehicleDetails[0],
    }),
  )

  renderRouter('/vehicles/00000000-0000-4000-8000-000000000001')

  expect(
    await screen.findByRole('heading', { name: 'Fiat Panda' }),
  ).toBeVisible()
  expect(screen.getByText('1.0 FireFly Hybrid')).toBeVisible()
})

test('renders routed API 404s through the root not-found boundary', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Vehicle not found' }),
    }),
  )

  renderRouter('/vehicles/missing')

  expect(
    await screen.findByRole('heading', { name: 'Pagina non trovata' }),
  ).toBeVisible()
  expect(screen.queryByText('Vehicle not found')).not.toBeInTheDocument()
})

test('retries a rendered loader failure and replaces it with detail content', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  const fetchMock = vi
    .fn()
    .mockRejectedValueOnce(new Error('API unavailable'))
    .mockResolvedValueOnce({
      ok: true,
      json: async () => mockVehicleDetails[0],
    })
  vi.stubGlobal('fetch', fetchMock)

  renderRouter('/vehicles/00000000-0000-4000-8000-000000000001')

  expect(await screen.findByRole('alert')).toHaveTextContent('API unavailable')
  fireEvent.click(screen.getByRole('button', { name: 'Riprova' }))

  expect(
    await screen.findByRole('heading', { name: 'Fiat Panda' }),
  ).toBeVisible()
  expect(fetchMock).toHaveBeenCalledTimes(2)
  expect(consoleError).toHaveBeenCalled()
})

test('restores rendered detail routes across back and forward navigation', async () => {
  const fetchMock = vi.fn().mockImplementation(async (url: string) => {
    if (url.endsWith('/vehicles/00000000-0000-4000-8000-000000000001')) {
      return { ok: true, json: async () => mockVehicleDetails[0] }
    }
    if (url.endsWith('/listings/30000000-0000-4000-8000-000000000001')) {
      return { ok: true, json: async () => mockListings[0] }
    }
    throw new Error(`Unexpected URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  const router = renderRouter(
    '/vehicles/00000000-0000-4000-8000-000000000001',
  )

  expect(
    await screen.findByRole('heading', { name: 'Fiat Panda' }),
  ).toBeVisible()

  await act(async () => {
    await router.navigate({
      to: '/listings/$listingId',
      params: { listingId: '30000000-0000-4000-8000-000000000001' },
    })
  })
  expect(
    await screen.findByRole('heading', {
      name: 'Fiat Panda 1.0 FireFly Hybrid',
    }),
  ).toBeVisible()

  await act(async () => {
    router.history.back()
    await router.load()
  })
  expect(
    await screen.findByRole('heading', { name: 'Fiat Panda' }),
  ).toBeVisible()

  await act(async () => {
    router.history.forward()
    await router.load()
  })
  expect(
    await screen.findByRole('heading', {
      name: 'Fiat Panda 1.0 FireFly Hybrid',
    }),
  ).toBeVisible()
})

function renderRouter(initialPath: string) {
  vi.stubGlobal('scrollTo', vi.fn())
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [initialPath] }),
    scrollRestoration: false,
  })
  render(createElement(RouterProvider, { router }), {
    container: document as unknown as HTMLElement,
  })
  return router
}
