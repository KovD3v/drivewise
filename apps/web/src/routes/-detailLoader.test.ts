import { isNotFound } from '@tanstack/react-router'
import { afterEach, expect, test, vi } from 'vitest'

import { fetchVehicle } from '../api/drivewise'
import { loadDetail } from './-detailLoader'

afterEach(() => {
  vi.unstubAllGlobals()
})

test('preserves ordinary loader failures for the retryable error boundary', async () => {
  const error = new Error('API unavailable')

  await expect(loadDetail(() => Promise.reject(error))).rejects.toBe(error)
})

test('converts API not-found failures into router not-found results', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Vehicle not found' }),
    }),
  )

  const result = await loadDetail(() => fetchVehicle('missing')).catch(
    (caughtError) => caughtError,
  )

  expect(isNotFound(result)).toBe(true)
})
