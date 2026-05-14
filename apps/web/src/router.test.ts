import { createMemoryHistory, createRouter } from '@tanstack/react-router'
import { expect, test } from 'vitest'

import { routeTree } from './routeTree.gen'

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
