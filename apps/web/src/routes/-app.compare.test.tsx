import { afterEach, expect, test, vi } from 'vitest'
import { isNotFound } from '@tanstack/react-router'
import carDetail from '@/test/fixtures/car-detail.synthetic.json'
import { Route } from './app.compare'

afterEach(() => { vi.unstubAllGlobals() })

type Deps = { vehicle?: string; spec?: string; with?: string; withSpec?: string }
type Loaded = { first: { vehicle: { id: string; seats: number | null }; specId?: string } | null }
const loader = Route.options.loader as unknown as (ctx: { deps: Deps }) => Promise<Loaded>

const base = carDetail.specs[0]!
const scored = { ...base, id: 'b9b0b7c0-0000-4000-8000-000000000002', seats: 7 }
const detail = { ...carDetail, specs: [base, scored] }

function serveCatalogue() {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => ({
    ok: true,
    json: async () => (url.includes('/vehicles?') ? [] : detail),
  })))
}

test('compare shows the exact version the link names, not the default one', async () => {
  serveCatalogue()
  const { first } = await loader({ deps: { vehicle: carDetail.id, spec: scored.id } })
  expect(first?.specId).toBe(scored.id)
  expect(first?.vehicle.seats).toBe(7)
})

test('an unknown version or a malformed id is a 404, never a silent switch', async () => {
  serveCatalogue()
  expect(isNotFound(await loader({ deps: { vehicle: carDetail.id, spec: 'missing-spec' } }).catch((e: unknown) => e))).toBe(true)
  expect(isNotFound(await loader({ deps: { vehicle: 'abc' } }).catch((e: unknown) => e))).toBe(true)
})
