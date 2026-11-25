import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

const navigate = vi.fn()
const search: { q?: string } = {}
const takeInitialQuery = vi.fn(() => '')
vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: Record<string, unknown>) => ({ options, useSearch: () => search }),
  useNavigate: () => navigate,
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))
vi.mock('@/components/app/GuidedCarFlow', () => ({ GuidedCarFlow: () => <p>guided car flow</p> }))
vi.mock('@/lib/analytics', () => ({ track: vi.fn(), takeInitialQuery: () => takeInitialQuery() }))

afterEach(() => { cleanup(); navigate.mockReset(); takeInitialQuery.mockClear(); delete search.q })

async function renderStart() {
  const { Route } = await import('./app.start')
  const Start = (Route as unknown as { options: { component: () => React.ReactElement } }).options.component
  render(<Start />)
}

test.each([['Moto', 'motorcycle'], ['Scooter', 'scooter']])('choosing %s opens the catalogue without a score', async (label, type) => {
  await renderStart()
  fireEvent.click(screen.getByRole('button', { name: label }))
  await waitFor(() => expect(navigate).toHaveBeenCalledWith({ to: '/app/catalog', search: { type } }))
})

test('choosing a car starts the guided decision', async () => {
  await renderStart()
  fireEvent.click(screen.getByRole('button', { name: 'Auto' }))
  expect(await screen.findByText('guided car flow')).toBeInTheDocument()
  expect(navigate).not.toHaveBeenCalled()
})

test('a ?q= search still consumes the stored landing query, so it cannot hijack a later visit', async () => {
  search.q = 'cerco uno scooter'
  await renderStart()
  await waitFor(() => expect(navigate).toHaveBeenCalledWith({ to: '/app/catalog', search: { type: 'scooter' } }))
  expect(takeInitialQuery).toHaveBeenCalledTimes(1)
})
