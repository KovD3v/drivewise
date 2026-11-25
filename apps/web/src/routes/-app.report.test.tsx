import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import guidedDecision from '@/test/fixtures/guided-decision.synthetic.json'
import { fetchGuidedDecision, type GuidedDecisionResponse } from '@/api/drivewise'
import { DECISION_STATE_KEY } from '@/lib/decision-state'

const search: { s?: string } = {}
vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: Record<string, unknown>) => ({ options, useSearch: () => search }),
  useNavigate: () => vi.fn(),
  Link: ({ children, to, params, search: linkSearch, onClick }: { children: React.ReactNode; to: string; params?: Record<string, string>; search?: Record<string, string | undefined>; onClick?: () => void }) => (
    <a data-to={to} data-params={JSON.stringify(params ?? {})} data-search={JSON.stringify(linkSearch ?? {})} onClick={(e) => { e.preventDefault(); onClick?.() }}>{children}</a>
  ),
}))
vi.mock('@/components/app/SaveAnalysisPrompt', () => ({ SaveAnalysisPrompt: () => null }))
vi.mock('@/components/app/AppHeader', () => ({ AppHeader: () => null }))
vi.mock('@/api/drivewise', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/drivewise')>()),
  fetchGuidedDecision: vi.fn(),
}))

// jsdom has no IntersectionObserver; framer-motion's whileInView needs one.
vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } })

afterEach(() => { cleanup(); vi.mocked(fetchGuidedDecision).mockReset(); localStorage.clear(); delete search.s })

const decision = guidedDecision as unknown as GuidedDecisionResponse
const winner = decision.previewRanking.groups[0]!.items[0]!

async function renderReport() {
  const { Route } = await import('./app.report')
  const Report = (Route as unknown as { options: { component: () => React.ReactElement } }).options.component
  return render(<Report />)
}

test('?s= loads the decision from the API with no local state and re-enables both CTAs', async () => {
  search.s = decision.decisionId
  vi.mocked(fetchGuidedDecision).mockResolvedValue(decision)
  await renderReport()

  const open = await screen.findByText(`Apri la scheda ${winner.vehicle.model}`)
  expect(fetchGuidedDecision).toHaveBeenCalledWith(decision.decisionId)
  expect(localStorage.getItem(DECISION_STATE_KEY)).toBeNull()

  const link = open.closest('a')!
  expect(link.dataset.to).toBe('/app/vehicle/$id')
  expect(JSON.parse(link.dataset.params!)).toEqual({ id: winner.vehicle.id })
  expect(JSON.parse(link.dataset.search!)).toEqual({ spec: winner.selected_spec.id, s: decision.decisionId })
  expect(link.closest('button')).toBeNull()

  localStorage.setItem(DECISION_STATE_KEY, '{"profile":{"vehicleType":"car"}}')
  const restart = screen.getByText('Rifai la Scelta Guidata').closest('a')!
  expect(restart.dataset.to).toBe('/app/start')
  fireEvent.click(restart)
  expect(localStorage.getItem(DECISION_STATE_KEY)).toBeNull()

  // The Advisor's per-vehicle missing factors stay visible, apart from the tradeoffs.
  expect(screen.getByText('Da verificare su questo veicolo')).toBeInTheDocument()
  expect(screen.getByText(/Dati mancanti nel catalogo: costo totale di possesso/)).toBeInTheDocument()
  expect(screen.getByText('Dati da aggiungere al tuo profilo: misure del garage.')).toBeInTheDocument()
  expect(screen.queryByText(/vehicle_dna_assessment|request\.garage/)).not.toBeInTheDocument()
})

test('a new decision id clears the previous result, and its error never shows the old winner', async () => {
  search.s = decision.decisionId
  vi.mocked(fetchGuidedDecision).mockResolvedValueOnce(decision)
  const view = await renderReport()
  await screen.findByText(`Apri la scheda ${winner.vehicle.model}`)

  search.s = 'another-decision'
  vi.mocked(fetchGuidedDecision).mockRejectedValueOnce(new Error('Decision not found'))
  const { Route } = await import('./app.report')
  const Report = (Route as unknown as { options: { component: () => React.ReactElement } }).options.component
  // Same mounted report, new ?s=: the effect must reset before loading the next decision.
  view.rerender(<Report />)

  expect(await screen.findByRole('alert')).toHaveTextContent('Decision not found')
  expect(screen.queryByText(`Apri la scheda ${winner.vehicle.model}`)).not.toBeInTheDocument()
  await waitFor(() => expect(fetchGuidedDecision).toHaveBeenLastCalledWith('another-decision'))

  // Back to a working decision: the previous error must not linger.
  search.s = decision.decisionId
  vi.mocked(fetchGuidedDecision).mockResolvedValueOnce(decision)
  view.rerender(<Report />)
  await screen.findByText(`Apri la scheda ${winner.vehicle.model}`)
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('without ?s= and without local state the report asks for the guided decision', async () => {
  await renderReport()
  expect(await screen.findByText('Nessun profilo decisionale attivo.')).toBeInTheDocument()
  expect(fetchGuidedDecision).not.toHaveBeenCalled()
})

test('with new and used groups the report opens on the stronger winner and switches condition', async () => {
  type Item = GuidedDecisionResponse['previewRanking']['groups'][number]['items'][number]
  const car = (model: string, id: string, score: number): Item => ({ ...winner, vehicle: { ...winner.vehicle, id, model }, score })
  search.s = decision.decisionId
  vi.mocked(fetchGuidedDecision).mockResolvedValue({
    ...decision,
    previewRanking: { ...decision.previewRanking, groups: [
      { condition: 'new', items: [car('Nuova Uno', 'a1b2c3d4-0000-4000-8000-000000000001', 70)] },
      { condition: 'used', items: [car('Usata Due', 'a1b2c3d4-0000-4000-8000-000000000002', 85)] },
    ] },
  })
  await renderReport()

  const open = await screen.findByText('Apri la scheda Usata Due')
  // With two groups the vehicle link names the condition, so the page shows that group's entry.
  expect(JSON.parse(open.closest('a')!.dataset.search!)).toMatchObject({ condition: 'used' })
  const switcher = screen.getByRole('group', { name: 'Classifica per condizione' })
  expect(switcher).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Usate · 85' })).toHaveAttribute('aria-pressed', 'true')

  fireEvent.click(screen.getByRole('button', { name: 'Nuove · 70' }))
  expect(await screen.findByText('Apri la scheda Nuova Uno')).toBeInTheDocument()
  expect(screen.queryByText('Apri la scheda Usata Due')).not.toBeInTheDocument()
})

test('a single condition group shows no condition switch', async () => {
  search.s = decision.decisionId
  vi.mocked(fetchGuidedDecision).mockResolvedValue(decision)
  await renderReport()
  await screen.findByText(`Apri la scheda ${winner.vehicle.model}`)
  expect(screen.queryByRole('group', { name: 'Classifica per condizione' })).not.toBeInTheDocument()
  const link = screen.getByText(`Apri la scheda ${winner.vehicle.model}`).closest('a')!
  expect(JSON.parse(link.dataset.search!)).not.toHaveProperty('condition')
})
