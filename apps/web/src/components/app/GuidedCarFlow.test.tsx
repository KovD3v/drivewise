import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GuidedCarFlow } from './GuidedCarFlow';
import { createGuidedDecision, addGuidedDecisionTurn, type GuidedDecisionResponse } from '@/api/drivewise';
import fixture from '@/test/fixtures/guided-decision.synthetic.json';

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => vi.fn(), Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a> }));
// Keep the real error helpers (isApiErrorCode); only the network calls are mocked.
vi.mock('@/api/drivewise', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/drivewise')>()),
  createGuidedDecision: vi.fn(), addGuidedDecisionTurn: vi.fn(), fetchGuidedDecision: vi.fn(),
}));
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => {}); });
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

const budgetQuestion = { id: 'budget_eur', type: 'number' as const, label: 'Budget massimo?', reason: 'Serve per il confronto.', constraints: { minimum: 1000, maximum: null, unit: 'EUR', options: [] as string[] } };
const response = {
  ...(fixture as unknown as GuidedDecisionResponse),
  decisionId: 'decision-123', profileVersion: 1, profileCompletion: 0.42, decisionConfidence: 0.61,
  missingInformation: [], nextQuestion: budgetQuestion,
  previewRanking: { status: 'blocked' as const, groups: [], assumptions: [], blockingReasons: [], scoringVersion: null },
  garageCompatibility: [], warnings: [], status: 'active' as const, message: '',
} satisfies GuidedDecisionResponse;

test('reference category intake preserves selected category, retry and versioned backend turns', async () => {
  vi.mocked(createGuidedDecision).mockRejectedValueOnce(new Error('Servizio non disponibile')).mockResolvedValueOnce(response);
  vi.mocked(addGuidedDecisionTurn).mockResolvedValue({ ...response, profileVersion: 2 });
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  expect(createGuidedDecision).not.toHaveBeenCalled();
  expect(screen.queryByPlaceholderText('Descrivi liberamente cosa cerchi')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Hatchback' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  await screen.findByRole('alert');
  expect(createGuidedDecision).toHaveBeenCalledWith('Cerco una compatta. Auto per la città');
  fireEvent.click(screen.getByRole('button', { name: 'Riprova' }));
  await screen.findByLabelText('Budget massimo?');
  expect(createGuidedDecision).toHaveBeenCalledTimes(2);
  fireEvent.change(screen.getByLabelText('Budget massimo?'), { target: { value: '18000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Conferma' }));
  await waitFor(() => expect(addGuidedDecisionTurn).toHaveBeenCalledWith('decision-123', '18000', 1));
});

test('unknown category adds no invented category and oversized requests never reach the API', async () => {
  render(<GuidedCarFlow initialQuery="" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  const input = await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.change(input, { target: { value: 'a'.repeat(2001) } });
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('2000');
  expect(createGuidedDecision).not.toHaveBeenCalled();
  vi.mocked(createGuidedDecision).mockResolvedValueOnce(response);
  fireEvent.change(input, { target: { value: 'Auto per la città' } });
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  await waitFor(() => expect(createGuidedDecision).toHaveBeenCalledWith('Auto per la città'));
});

test.each([
  ['parking', 'single_select', 'Nessun posto auto'],
  ['constraint_modes', 'multi_select', 'Nessun vincolo obbligatorio'],
] as const)('submits canonical none for %s without using its display label', async (id, type, label) => {
  const next = { ...response, nextQuestion: { ...budgetQuestion, id, type, constraints: { ...budgetQuestion.constraints, options: ['none'] } } };
  vi.mocked(createGuidedDecision).mockResolvedValue(next);
  vi.mocked(addGuidedDecisionTurn).mockResolvedValue({ ...response, profileVersion: 2 });
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  fireEvent.click(await screen.findByRole('button', { name: label }));
  if (type === 'multi_select') fireEvent.click(screen.getByRole('button', { name: 'Conferma selezione' }));
  await waitFor(() => expect(addGuidedDecisionTurn).toHaveBeenCalledWith('decision-123', 'none', 1));
  expect(await screen.findByText(label)).toBeInTheDocument();
});

test('a failed turn whose resync brings a newer question never resends the old answer', async () => {
  const { fetchGuidedDecision } = await import('@/api/drivewise');
  vi.mocked(createGuidedDecision).mockResolvedValue(response);
  vi.mocked(addGuidedDecisionTurn).mockRejectedValueOnce(new Error('Conflitto di versione'));
  const newer = { ...response, profileVersion: 2, nextQuestion: { ...budgetQuestion, id: 'annual_km', label: 'Quanti km fai?' } };
  vi.mocked(fetchGuidedDecision).mockResolvedValue(newer);
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  fireEvent.change(await screen.findByLabelText('Budget massimo?'), { target: { value: '18000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Conferma' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Conflitto di versione');
  await screen.findByLabelText('Quanti km fai?');
  expect(screen.queryByRole('button', { name: 'Riprova' })).not.toBeInTheDocument();
});

test('a failed turn on an unchanged question still offers the retry', async () => {
  const { fetchGuidedDecision } = await import('@/api/drivewise');
  vi.mocked(createGuidedDecision).mockResolvedValue(response);
  vi.mocked(addGuidedDecisionTurn).mockRejectedValueOnce(new Error('Servizio non disponibile')).mockResolvedValueOnce({ ...response, profileVersion: 2 });
  vi.mocked(fetchGuidedDecision).mockResolvedValue(response);
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  fireEvent.change(await screen.findByLabelText('Budget massimo?'), { target: { value: '18000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Conferma' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Riprova' }));
  await waitFor(() => expect(addGuidedDecisionTurn).toHaveBeenLastCalledWith('decision-123', '18000', 1));
});

test('a capped session explains the turn limit, offers the report and restarts cleanly', async () => {
  const { fetchGuidedDecision } = await import('@/api/drivewise');
  const ranked = { ...response, previewRanking: (fixture as unknown as GuidedDecisionResponse).previewRanking };
  vi.mocked(createGuidedDecision).mockResolvedValue(ranked);
  vi.mocked(fetchGuidedDecision).mockResolvedValue(ranked);
  // The real API answer: 409 with an object detail, which the client turns into an error code.
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'max_turns_reached' } }), { status: 409 })));
  const actual = await vi.importActual<typeof import('@/api/drivewise')>('@/api/drivewise');
  vi.mocked(addGuidedDecisionTurn).mockImplementation(actual.addGuidedDecisionTurn);
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  fireEvent.change(await screen.findByLabelText('Budget massimo?'), { target: { value: '18000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Conferma' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('numero massimo di risposte');
  expect(screen.getByRole('alert')).toHaveTextContent('apri il Decision Report');
  // No input accepts another answer, and no retry resends the capped one.
  expect(screen.queryByLabelText('Budget massimo?')).not.toBeInTheDocument();
  expect(screen.queryByPlaceholderText("Aggiungi o correggi un'esigenza")).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Riprova' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Mostrami il Decision Report' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Inizia una nuova sessione' }));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Non lo so ancora' })).toBeInTheDocument();
});
