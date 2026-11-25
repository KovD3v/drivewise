import { afterEach, expect, test, vi } from 'vitest'
import { isNotFound } from '@tanstack/react-router'
import carDetail from '@/test/fixtures/car-detail.synthetic.json'
import { Route } from './app.vehicle.$id'

afterEach(() => { vi.unstubAllGlobals() })

type Loader = (ctx: { params: { id: string } }) => Promise<unknown>
const loader = Route.options.loader as unknown as Loader

test('a malformed vehicle id is a 404 and never reaches the API', async () => {
  vi.stubGlobal('fetch', vi.fn())
  const error = await loader({ params: { id: 'abc' } }).catch((e: unknown) => e)
  expect(isNotFound(error)).toBe(true)
  expect(fetch).not.toHaveBeenCalled()
})

test('a missing vehicle is a 404, but an API outage stays an error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: 'Vehicle not found' }) }))
  expect(isNotFound(await loader({ params: { id: carDetail.id } }).catch((e: unknown) => e))).toBe(true)

  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: 'Catalog unavailable' }) }))
  const outage = await loader({ params: { id: carDetail.id } }).catch((e: unknown) => e)
  expect(isNotFound(outage)).toBe(false)
  expect(outage).toBeInstanceOf(Error)
})

test('the page accepts the version and decision it should show', () => {
  const validate = Route.options.validateSearch as unknown as (s: Record<string, unknown>) => unknown
  expect(validate({ spec: 'spec-1', s: 'decision-1', other: 1 })).toEqual({ spec: 'spec-1', s: 'decision-1' })
  expect(validate({ spec: 3 })).toEqual({ spec: undefined, s: undefined })
})
