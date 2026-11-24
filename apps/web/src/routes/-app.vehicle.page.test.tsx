import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import carDetail from '@/test/fixtures/car-detail.synthetic.json'
import type { VehicleDetail } from '@/api/drivewise'
import { fromApiVehicle } from '@/services/vehicleService'

const base = carDetail.specs[0]!
const other = { ...base, id: 'b9b0b7c0-0000-4000-8000-000000000002', seats: 7 }
const detail = { ...carDetail, specs: [base, other] } as unknown as VehicleDetail
const search: { spec?: string; s?: string } = {}

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: Record<string, unknown>) => ({
    options,
    useSearch: () => search,
    useLoaderData: () => ({ vehicle: fromApiVehicle(detail), detail }),
  }),
  notFound: () => new Error('not found'),
  useRouter: () => ({ invalidate: vi.fn() }),
  Link: ({ children, to, search: linkSearch }: { children: React.ReactNode; to: string; search?: Record<string, string | undefined> }) => (
    <a data-to={to} data-search={JSON.stringify(linkSearch ?? {})}>{children}</a>
  ),
}))
vi.mock('@/components/app/AppHeader', () => ({ AppHeader: () => null }))

// jsdom has no IntersectionObserver; framer-motion's whileInView needs one.
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => {}); vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }) })
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); delete search.spec; delete search.s })

async function renderVehicle() {
  const { Route } = await import('./app.vehicle.$id')
  const Page = (Route as unknown as { options: { component: () => React.ReactElement } }).options.component
  render(<Page />)
}

test('the version the link names is the one shown, compared and analysed', async () => {
  search.spec = other.id
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ estimated_costs: { market_reference_price_eur: null }, red_flags: [], checklist: [], warnings: [], assumptions: [], missing_data: [] }),
  }))
  await renderVehicle()

  fireEvent.click(screen.getByText('Tutte le specifiche disponibili'))
  // The spec table shows the named version's 7 seats, not the default version's 5.
  const seats = (await screen.findAllByText('Posti')).map((label) => label.parentElement?.textContent)
  expect(seats).toContain('Posti7')
  expect(seats).not.toContain('Posti5')

  const compare = screen.getByText('Confronta').closest('a')!
  expect(compare.dataset.to).toBe('/app/compare')
  expect(JSON.parse(compare.dataset.search!)).toEqual({ vehicle: carDetail.id, spec: other.id })

  fireEvent.click(screen.getByRole('button', { name: 'Quanto costa?' }))
  await waitFor(() => expect(fetch).toHaveBeenCalled())
  const [, init] = vi.mocked(fetch).mock.calls[0]!
  expect(JSON.parse(String(init!.body))).toMatchObject({ vehicle_id: carDetail.id, spec_id: other.id })
})

test('an unknown version falls back to the default one, and the compare link names it', async () => {
  search.spec = 'not-a-version'
  vi.stubGlobal('fetch', vi.fn())
  await renderVehicle()
  const compare = screen.getByText('Confronta').closest('a')!
  expect(JSON.parse(compare.dataset.search!)).toEqual({ vehicle: carDetail.id, spec: base.id })
})
